from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models, schemas
from .auth import get_current_user
from sqlalchemy import func
from datetime import datetime, timedelta

orders_router = APIRouter()

@orders_router.get("/", response_model=List[schemas.Order])
def get_orders(
    skip: int = 0, 
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get all orders for the current user's account
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    orders = db.query(models.Order)\
        .filter(models.Order.user_id == user_id)\
        .offset(skip)\
        .all()
        
    return orders

@orders_router.get("/has-orders", response_model=dict)
def check_has_orders(
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Check if a user has ever had any orders in the system.
    Used by the dashboard to determine if the "Connect POS provider" prompt should be shown.
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    # Check if there's at least one order in the database for this user
    has_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.user_id == user_id
    ).scalar() > 0
    
    return {"has_orders": has_orders}




@orders_router.post("/", response_model=schemas.Order, status_code=status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Create a new order with items, associated with the current user's account
    """
    # Calculate total amount from items
    total_amount = sum(item.unit_price * item.quantity for item in order.items)
    
    # Create order with user_id
    db_order = models.Order(
        order_date=order.order_date,
        total_amount=total_amount,
        user_id=current_user.id  # Associate with current user
    )
    db.add(db_order)
    db.flush()  # Flush to get the order ID
    
    # Create order items
    for item in order.items:
        # Verify item exists and belongs to the user
        db_item = db.query(models.Item).filter(
            models.Item.id == item.item_id,
            models.Item.user_id == current_user.id
        ).first()
        if not db_item:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Item with ID {item.item_id} not found")
            
        order_item = models.OrderItem(
            order_id=db_order.id,
            item_id=item.item_id,
            quantity=item.quantity,
            unit_price=item.unit_price
        )
        db.add(order_item)
    
    db.commit()
    db.refresh(db_order)
    return db_order

@orders_router.get("/range", response_model=List[schemas.Order])
def get_orders_by_date_range(
    start_date: str,
    end_date: str,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get orders within a date range for the user's account
    """
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        )
    
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    orders = db.query(models.Order).filter(
        models.Order.order_date >= start,
        models.Order.order_date <= end,
        models.Order.user_id == user_id
    ).all()
    
    return orders

@orders_router.get("/analytics", response_model=schemas.OrderAnalytics)
def get_order_analytics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get order analytics data
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    # Start with query filtered by user_id
    query = db.query(models.Order).filter(models.Order.user_id == user_id)
    
    # Apply date filters if provided
    if start_date and end_date:
        try:
            # First try standard ISO format
            try:
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
            except ValueError:
                # Fallback to simple date format
                start = datetime.strptime(start_date, '%Y-%m-%d')
                end = datetime.strptime(end_date, '%Y-%m-%d')
                # Add a day to end date to make it inclusive
                end = end.replace(hour=23, minute=59, second=59)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Invalid date format. Use format YYYY-MM-DD"
            )
        
        query = query.filter(
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    
    # Get total orders and revenue
    total_orders = query.count()
    total_revenue = db.query(func.sum(models.Order.total_amount)).scalar() or 0
    
    # Calculate average order value
    average_order_value = total_revenue / total_orders if total_orders > 0 else 0
    
    # Get top selling items
    top_items_query = db.query(
        models.Item.id,
        models.Item.name,
        func.sum(models.OrderItem.quantity).label("total_quantity"),
        func.sum(models.OrderItem.quantity * models.OrderItem.unit_price).label("total_revenue")
    ).join(
        models.OrderItem, models.Item.id == models.OrderItem.item_id
    ).join(
        models.Order, models.OrderItem.order_id == models.Order.id
    ).filter(
        # Ensure only items belonging to current user are included
        models.Item.user_id == user_id,
        models.Order.user_id == user_id
    )
    
    # Apply date filters if provided
    if start_date and end_date:
        top_items_query = top_items_query.filter(
            models.Order.order_date >= start,
            models.Order.order_date <= end
        )
    
    top_items = top_items_query.group_by(
        models.Item.id
    ).order_by(
        func.sum(models.OrderItem.quantity).desc()
    ).limit(5).all()
    
    top_selling_items = [
        {
            "id": item.id,
            "name": item.name,
            "total_quantity": item.total_quantity,
            "total_revenue": item.total_revenue
        }
        for item in top_items
    ]
    
    return {
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "average_order_value": average_order_value,
        "top_selling_items": top_selling_items
    }

@orders_router.get("/{order_id}", response_model=schemas.Order)
def get_order(
    order_id: int, 
    account_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Get a specific order by ID, ensuring it belongs to the user's account
    """
    # Filter by the current user's ID unless specifically requesting another account's data
    user_id = account_id if account_id else current_user.id
    
    order = db.query(models.Order).filter(
        models.Order.id == order_id,
        models.Order.user_id == user_id
    ).first()
    
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found or you don't have permission to view it")
        
    return order