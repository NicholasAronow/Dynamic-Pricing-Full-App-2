"""
Admin dashboard API routes with comprehensive system management.
"""
import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc, text, and_, or_
from pydantic import BaseModel
import csv
import io

# Ensure we can import from parent directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import get_db
from auth import get_current_admin_user
import models
import schemas

admin_router = APIRouter(tags=["admin"])

# Pydantic models for admin responses
class AdminStats(BaseModel):
    total_users: int
    active_users: int
    admin_users: int
    total_businesses: int
    total_orders: int
    total_items: int
    total_revenue: float
    users_last_30_days: int
    orders_last_30_days: int
    revenue_last_30_days: float
    orders_today: int
    revenue_today: float
    subscription_breakdown: Dict[str, int]
    pos_integrations: int
    avg_order_value: float

class UserSummary(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    is_admin: bool
    subscription_tier: Optional[str]
    created_at: datetime
    business_name: Optional[str]
    total_orders: int
    total_revenue: float
    last_login: Optional[datetime]

class BusinessSummary(BaseModel):
    id: int
    business_name: str
    industry: Optional[str]
    owner_email: str
    total_items: int
    total_orders: int
    total_revenue: float
    created_at: datetime

class SystemHealth(BaseModel):
    database_status: str
    total_tables: int
    recent_errors: List[str]
    performance_metrics: Dict[str, Any]

class UserMenuItem(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    current_price: float
    cost: Optional[float]
    created_at: datetime
    total_orders: int
    total_revenue: float

class UserOrder(BaseModel):
    id: int
    order_date: datetime
    total_amount: float
    total_cost: Optional[float]
    gross_margin: Optional[float]
    items_count: int
    pos_id: Optional[str]

class DetailedUserInfo(BaseModel):
    id: int
    email: str
    name: Optional[str]
    is_active: bool
    is_admin: bool
    subscription_tier: Optional[str]
    created_at: datetime
    business_name: Optional[str]
    business_industry: Optional[str]
    total_orders: int
    total_revenue: float
    total_items: int
    pos_connected: bool
    last_order_date: Optional[datetime]
    avg_order_value: float
    menu_items: List[UserMenuItem]
    recent_orders: List[UserOrder]

@admin_router.get("/stats", response_model=AdminStats)
async def get_admin_stats(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive system statistics"""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    today = datetime.utcnow().date()
    
    # Basic counts
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    admin_users = db.query(models.User).filter(models.User.is_admin == True).count()
    total_businesses = db.query(models.BusinessProfile).count()
    total_orders = db.query(models.Order).count()
    total_items = db.query(models.Item).count()
    
    # Revenue calculations
    total_revenue = db.query(func.sum(models.Order.total_amount)).scalar() or 0.0
    
    # Recent activity (30 days)
    users_last_30_days = db.query(models.User).filter(
        models.User.created_at >= thirty_days_ago
    ).count()
    
    orders_last_30_days = db.query(models.Order).filter(
        models.Order.order_date >= thirty_days_ago
    ).count()
    
    revenue_last_30_days = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.order_date >= thirty_days_ago
    ).scalar() or 0.0
    
    # Today's activity
    orders_today = db.query(models.Order).filter(
        func.date(models.Order.order_date) == today
    ).count()
    
    revenue_today = db.query(func.sum(models.Order.total_amount)).filter(
        func.date(models.Order.order_date) == today
    ).scalar() or 0.0
    
    # Subscription breakdown
    subscription_stats = db.query(
        models.User.subscription_tier,
        func.count(models.User.id)
    ).group_by(models.User.subscription_tier).all()
    
    subscription_breakdown = {tier or 'free': count for tier, count in subscription_stats}
    
    # POS integrations
    pos_integrations = db.query(models.POSIntegration).count()
    
    # Average order value
    avg_order_value = db.query(func.avg(models.Order.total_amount)).scalar() or 0.0
    
    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        admin_users=admin_users,
        total_businesses=total_businesses,
        total_orders=total_orders,
        total_items=total_items,
        total_revenue=total_revenue,
        users_last_30_days=users_last_30_days,
        orders_last_30_days=orders_last_30_days,
        revenue_last_30_days=revenue_last_30_days,
        orders_today=orders_today,
        revenue_today=revenue_today,
        subscription_breakdown=subscription_breakdown,
        pos_integrations=pos_integrations,
        avg_order_value=avg_order_value
    )

@admin_router.get("/users", response_model=List[UserSummary])
async def get_all_users(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None)
):
    """Get all users with business and activity information"""
    query = db.query(models.User).options(
        joinedload(models.User.business)
    )
    
    # Apply search filter if provided
    if search:
        query = query.filter(
            or_(
                models.User.email.ilike(f"%{search}%"),
                models.User.name.ilike(f"%{search}%")
            )
        )
    
    users = query.offset(skip).limit(limit).all()
    
    user_summaries = []
    for user in users:
        # Get user's order statistics
        order_stats = db.query(
            func.count(models.Order.id).label('total_orders'),
            func.sum(models.Order.total_amount).label('total_revenue')
        ).filter(models.Order.user_id == user.id).first()
        
        user_summaries.append(UserSummary(
            id=user.id,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            subscription_tier=user.subscription_tier,
            created_at=user.created_at,
            business_name=user.business.business_name if user.business else None,
            total_orders=order_stats.total_orders or 0,
            total_revenue=order_stats.total_revenue or 0.0,
            last_login=None  # Would need to track login times separately
        ))
    
    return user_summaries

@admin_router.get("/businesses", response_model=List[BusinessSummary])
async def get_all_businesses(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """Get all businesses with activity information"""
    businesses = db.query(models.BusinessProfile).options(
        joinedload(models.BusinessProfile.owner)
    ).offset(skip).limit(limit).all()
    
    business_summaries = []
    for business in businesses:
        # Get business statistics
        total_items = db.query(models.Item).filter(
            models.Item.user_id == business.user_id
        ).count()
        
        order_stats = db.query(
            func.count(models.Order.id).label('total_orders'),
            func.sum(models.Order.total_amount).label('total_revenue')
        ).filter(models.Order.user_id == business.user_id).first()
        
        business_summaries.append(BusinessSummary(
            id=business.id,
            business_name=business.business_name,
            industry=business.industry,
            owner_email=business.owner.email,
            total_items=total_items,
            total_orders=order_stats.total_orders or 0,
            total_revenue=order_stats.total_revenue or 0.0,
            created_at=business.created_at
        ))
    
    return business_summaries

@admin_router.post("/users/{user_id}/toggle-admin")
async def toggle_user_admin_status(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle admin status for a user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent removing admin status from the last admin
    if user.is_admin:
        admin_count = db.query(models.User).filter(models.User.is_admin == True).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin status from the last admin user"
            )
    
    user.is_admin = not user.is_admin
    db.commit()
    
    return {
        "message": f"User {user.email} admin status {'enabled' if user.is_admin else 'disabled'}",
        "is_admin": user.is_admin
    }

@admin_router.post("/users/{user_id}/toggle-active")
async def toggle_user_active_status(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Toggle active status for a user"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = not user.is_active
    db.commit()
    
    return {
        "message": f"User {user.email} {'activated' if user.is_active else 'deactivated'}",
        "is_active": user.is_active
    }

@admin_router.get("/users/{user_id}/details", response_model=DetailedUserInfo)
async def get_user_details(
    user_id: int,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific user including menu items and orders"""
    # Get user with business profile
    user = db.query(models.User).options(
        joinedload(models.User.business)
    ).filter(models.User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's menu items with order statistics
    menu_items_query = db.query(
        models.Item,
        func.count(models.OrderItem.id).label('total_orders'),
        func.coalesce(func.sum(models.OrderItem.quantity * models.OrderItem.unit_price), 0).label('total_revenue')
    ).outerjoin(
        models.OrderItem, models.Item.id == models.OrderItem.item_id
    ).filter(
        models.Item.user_id == user_id
    ).group_by(models.Item.id).all()
    
    menu_items = [
        UserMenuItem(
            id=item.id,
            name=item.name,
            description=item.description,
            category=item.category,
            current_price=item.current_price,
            cost=item.cost,
            created_at=item.created_at,
            total_orders=total_orders,
            total_revenue=float(total_revenue)
        )
        for item, total_orders, total_revenue in menu_items_query
    ]
    
    # Get user's recent orders with item count
    recent_orders_query = db.query(
        models.Order,
        func.count(models.OrderItem.id).label('items_count')
    ).outerjoin(
        models.OrderItem, models.Order.id == models.OrderItem.order_id
    ).filter(
        models.Order.user_id == user_id
    ).group_by(models.Order.id).order_by(
        desc(models.Order.order_date)
    ).limit(20).all()
    
    recent_orders = [
        UserOrder(
            id=order.id,
            order_date=order.order_date,
            total_amount=order.total_amount,
            total_cost=order.total_cost,
            gross_margin=order.gross_margin,
            items_count=items_count,
            pos_id=order.pos_id
        )
        for order, items_count in recent_orders_query
    ]
    
    # Calculate user statistics
    total_orders = db.query(models.Order).filter(models.Order.user_id == user_id).count()
    total_revenue = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.user_id == user_id
    ).scalar() or 0.0
    total_items = db.query(models.Item).filter(models.Item.user_id == user_id).count()
    
    # Get last order date
    last_order = db.query(models.Order).filter(
        models.Order.user_id == user_id
    ).order_by(desc(models.Order.order_date)).first()
    
    avg_order_value = (total_revenue / total_orders) if total_orders > 0 else 0.0
    
    return DetailedUserInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        subscription_tier=user.subscription_tier,
        created_at=user.created_at,
        business_name=user.business.business_name if user.business else None,
        business_industry=user.business.industry if user.business else None,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_items=total_items,
        pos_connected=user.pos_connected,
        last_order_date=last_order.order_date if last_order else None,
        avg_order_value=avg_order_value,
        menu_items=menu_items,
        recent_orders=recent_orders
    )

@admin_router.post("/users/{user_id}/export")
async def start_user_data_export(
    user_id: int,
    data_type: str = Query(..., description="Type of data to export: 'menu_items', 'orders', or 'all'"),
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Start background CSV export task to prevent timeouts"""
    from tasks import generate_user_csv_task
    
    # Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate data_type
    if data_type not in ["menu_items", "orders", "all"]:
        raise HTTPException(status_code=400, detail="Invalid data_type. Must be 'menu_items', 'orders', or 'all'")
    
    try:
        # Start the background CSV generation task
        task = generate_user_csv_task.delay(user_id, data_type)
        
        return {
            "success": True,
            "task_id": task.id,
            "message": f"CSV export started for user {user_id}. Use the task_id to check progress.",
            "status": "PENDING"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start CSV export: {str(e)}")


@admin_router.get("/users/{user_id}/export/status/{task_id}")
async def get_csv_export_status(
    user_id: int,
    task_id: str,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Check the status of a CSV export task"""
    from tasks import get_csv_generation_status
    
    # Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Get task status
        status_result = get_csv_generation_status(task_id)
        return status_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@admin_router.get("/users/{user_id}/export/download/{task_id}")
async def download_csv_export(
    user_id: int,
    task_id: str,
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Download the completed CSV export"""
    from tasks import get_csv_generation_status
    
    # Validate user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Get task status and result
        status_result = get_csv_generation_status(task_id)
        
        if status_result["task_status"] != "COMPLETED":
            raise HTTPException(
                status_code=400, 
                detail=f"CSV export is not ready. Current status: {status_result['task_status']}"
            )
        
        if not status_result.get("result", {}).get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"CSV export failed: {status_result.get('result', {}).get('error', 'Unknown error')}"
            )
        
        # Get CSV content and filename from task result
        result = status_result["result"]
        csv_content = result["csv_content"]
        filename = result["filename"]
        
        # Return CSV as downloadable file
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download CSV: {str(e)}")


@admin_router.get("/system-health", response_model=SystemHealth)
async def get_system_health(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """Get system health and performance metrics"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        database_status = "healthy"
    except Exception as e:
        database_status = f"error: {str(e)}"
    
    # Count tables (simplified)
    total_tables = len(models.Base.metadata.tables)
    
    # Performance metrics (simplified)
    performance_metrics = {
        "active_connections": 1,  # Would need actual connection pool info
        "avg_query_time": "< 100ms",  # Would need actual metrics
        "cache_hit_ratio": "95%"  # Would need actual cache metrics
    }
    
    return SystemHealth(
        database_status=database_status,
        total_tables=total_tables,
        recent_errors=[],  # Would need error logging system
        performance_metrics=performance_metrics
    )

@admin_router.get("/activity-log")
async def get_activity_log(
    current_admin: models.User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=30)
):
    """Get recent system activity"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Recent user registrations
    recent_users = db.query(models.User).filter(
        models.User.created_at >= start_date
    ).order_by(desc(models.User.created_at)).limit(10).all()
    
    # Recent orders
    recent_orders = db.query(models.Order).filter(
        models.Order.order_date >= start_date
    ).order_by(desc(models.Order.order_date)).limit(10).all()
    
    # Recent price changes
    recent_price_changes = db.query(models.PriceHistory).filter(
        models.PriceHistory.changed_at >= start_date
    ).order_by(desc(models.PriceHistory.changed_at)).limit(10).all()
    
    return {
        "recent_users": [
            {
                "email": user.email,
                "name": user.name,
                "created_at": user.created_at
            } for user in recent_users
        ],
        "recent_orders": [
            {
                "id": order.id,
                "total_amount": order.total_amount,
                "order_date": order.order_date,
                "user_id": order.user_id
            } for order in recent_orders
        ],
        "recent_price_changes": [
            {
                "item_id": change.item_id,
                "previous_price": change.previous_price,
                "new_price": change.new_price,
                "change_reason": change.change_reason,
                "changed_at": change.changed_at
            } for change in recent_price_changes
        ]
    }
