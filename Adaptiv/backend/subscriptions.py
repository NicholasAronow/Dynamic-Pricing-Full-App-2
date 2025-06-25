import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
import models
from auth import get_current_user

# Initialize Stripe with API key from environment variable
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

router = APIRouter()

class SubscriptionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

class CustomerPortalRequest(BaseModel):
    return_url: str

class SubscriptionStatus(BaseModel):
    active: bool
    subscription_id: Optional[str] = None
    current_period_end: Optional[str] = None
    plan: Optional[str] = None

class PriceInfo(BaseModel):
    id: str
    product_id: str
    active: bool
    currency: str
    unit_amount: int
    nickname: Optional[str] = None
    recurring: Optional[dict] = None

@router.post("/create-checkout-session")
async def create_checkout_session(
    req: SubscriptionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a Stripe Checkout session for subscription"""
    try:
        # Check if the user already has a Stripe customer ID
        if not current_user.stripe_customer_id:
            # Create a new customer in Stripe
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.email.split('@')[0],  # Use the part before @ in email as name
                metadata={
                    "user_id": str(current_user.id)
                }
            )
            
            # Save the Stripe customer ID to the user record
            current_user.stripe_customer_id = customer.id
            db.commit()
        else:
            # Use the existing customer
            customer = current_user.stripe_customer_id
            
        # Create the checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": req.price_id,
                    "quantity": 1
                }
            ],
            mode="subscription",
            success_url=req.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=req.cancel_url,
            metadata={
                "user_id": str(current_user.id)
            }
        )
        
        return {"url": checkout_session.url}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/customer-portal")
async def create_customer_portal(
    req: CustomerPortalRequest,
    current_user: models.User = Depends(get_current_user)
):
    """Create a Stripe Customer Portal session for managing subscription"""
    try:
        if not current_user.stripe_customer_id:
            raise HTTPException(status_code=400, detail="No subscription found for this user")
        
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=req.return_url
        )
        
        return {"url": portal_session.url}
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/product-prices")
async def get_product_prices(productId: str):
    """Get prices for a specific product ID"""
    try:
        # Retrieve all prices for the given product
        prices = stripe.Price.list(
            product=productId,
            active=True,
            expand=["data.product"]
        )
        
        # Format the response
        result = {
            "product_id": productId,
            "prices": [{
                "id": price.id,
                "product_id": price.product.id if hasattr(price, 'product') else productId,
                "active": price.active,
                "currency": price.currency,
                "unit_amount": price.unit_amount,
                "nickname": price.nickname if hasattr(price, 'nickname') else None,
                "recurring": price.recurring if hasattr(price, 'recurring') else None
            } for price in prices.data]
        }
        
        return result
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Stripe error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving prices: {str(e)}"
        )

@router.get("/subscription-status")
async def get_subscription_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the subscription status for the current user"""
    try:
        # Check if the user has a Stripe customer ID
        if not current_user.stripe_customer_id:
            return SubscriptionStatus(active=False)
        
        # Retrieve the customer's subscriptions from Stripe
        subscriptions = stripe.Subscription.list(
            customer=current_user.stripe_customer_id,
            status="active",
            expand=["data.default_payment_method"]
        )
        
        # If there are no active subscriptions, return inactive
        if not subscriptions or not subscriptions.get('data') or len(subscriptions.get('data', [])) == 0:
            return SubscriptionStatus(active=False)
        
        # Get the latest subscription
        subscription = subscriptions.get('data')[0]
        
        # Get the product details for the subscription
        # Access subscription attributes safely using dict-style access
        items_data = subscription.get('items', {}).get('data', []) if hasattr(subscription, 'get') else subscription.items.data
        
        if not items_data or len(items_data) == 0:
            return SubscriptionStatus(active=False)
            
        # Get the price and product ID
        first_item = items_data[0]
        price = first_item.get('price') if hasattr(first_item, 'get') else first_item.price
        product_id = price.get('product') if hasattr(price, 'get') else price.product
        
        # Retrieve product details
        product = stripe.Product.retrieve(product_id)
        product_name = product.get('name') if hasattr(product, 'get') else product.name
        
        # Get subscription details
        sub_id = subscription.get('id') if hasattr(subscription, 'get') else subscription.id
        period_end = subscription.get('current_period_end') if hasattr(subscription, 'get') else subscription.current_period_end
        
        return SubscriptionStatus(
            active=True,
            subscription_id=sub_id,
            current_period_end=str(period_end),
            plan=product_name
        )
    
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    """Handle Stripe webhook events"""
    try:
        # Get the request body
        payload = await request.body()
        
        # Verify the webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=stripe_signature,
                secret=stripe_webhook_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        
        # Handle the event
        if event.type == 'checkout.session.completed':
            session = event.data.object
            # Set up the subscription
            handle_checkout_completed(session)
        elif event.type == 'invoice.paid':
            invoice = event.data.object
            # Continue to provision the subscription
            handle_invoice_paid(invoice)
        elif event.type == 'invoice.payment_failed':
            invoice = event.data.object
            # The payment failed or the customer does not have a valid payment method
            handle_invoice_payment_failed(invoice)
        
        return {"status": "success"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def handle_checkout_completed(session):
    """Handle checkout.session.completed event"""
    # This is where you would provision the subscription
    # For example, update the user's subscription status in your database
    customer_id = session.get('customer')
    subscription_id = session.get('subscription')
    user_id = session.get('metadata', {}).get('user_id')
    
    # TODO: Update user subscription status in database
    
def handle_invoice_paid(invoice):
    """Handle invoice.paid event"""
    # This is where you would handle a successful payment
    # For example, extend the user's subscription period
    customer_id = invoice.get('customer')
    subscription_id = invoice.get('subscription')
    
    # TODO: Update user subscription status in database
    
def handle_invoice_payment_failed(invoice):
    """Handle invoice.payment_failed event"""
    # This is where you would handle a failed payment
    # For example, notify the user that their payment failed
    customer_id = invoice.get('customer')
    subscription_id = invoice.get('subscription')
    
    # TODO: Update user subscription status in database and send notification
