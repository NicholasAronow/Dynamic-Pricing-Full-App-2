from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from typing import Optional, List, Any, Dict
from datetime import datetime

# Auth Schemas
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(UserBase):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Business Profile Schemas
class BusinessProfileBase(BaseModel):
    business_name: str
    industry: str
    company_size: str
    founded_year: Optional[int] = None
    description: Optional[str] = None

class BusinessProfileCreate(BusinessProfileBase):
    pass

class BusinessProfileUpdate(BusinessProfileBase):
    business_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None

class BusinessProfile(BusinessProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Complete User with Profile
class UserWithProfile(User):
    business: Optional[BusinessProfile] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Item Schemas
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    current_price: float
    cost: Optional[float] = None

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    current_price: Optional[float] = None
    cost: Optional[float] = None

class Item(ItemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Price History Schemas
class PriceHistoryBase(BaseModel):
    item_id: int
    previous_price: float
    new_price: float
    change_reason: Optional[str] = None

class PriceHistoryCreate(PriceHistoryBase):
    pass

class PriceHistory(PriceHistoryBase):
    id: int
    changed_at: datetime
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Price Simulation Schema (for testing without Square API)
class PriceSimulation(BaseModel):
    item_id: int
    new_price: float
    change_reason: Optional[str] = "Price simulation"

# Competitor Item Schemas
class CompetitorItemBase(BaseModel):
    competitor_name: str
    item_name: str
    description: Optional[str] = None
    category: str
    price: float
    similarity_score: Optional[float] = None
    url: Optional[str] = None

class CompetitorItemCreate(CompetitorItemBase):
    pass

class CompetitorItemUpdate(CompetitorItemBase):
    competitor_name: Optional[str] = None
    item_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    similarity_score: Optional[float] = None
    url: Optional[str] = None

class CompetitorItem(CompetitorItemBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Order Item Schemas
class OrderItemBase(BaseModel):
    item_id: int
    quantity: int
    unit_price: float

    @validator('quantity')
    def validate_positive_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        return v

class OrderItemCreate(OrderItemBase):
    pass

class OrderItem(OrderItemBase):
    id: int
    order_id: int
    subtotal: float
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Order Schemas
class OrderBase(BaseModel):
    order_date: datetime
    total_amount: float

class OrderCreateItem(BaseModel):
    item_id: int
    quantity: int
    unit_price: float

class OrderCreate(BaseModel):
    order_date: datetime
    items: List[OrderCreateItem]
    
    @validator('items')
    def validate_items_not_empty(cls, v):
        if not v:
            raise ValueError('Order must contain at least one item')
        return v

class Order(OrderBase):
    id: int
    created_at: datetime
    items: List[OrderItem] = []
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Order Analytics Response
class OrderAnalytics(BaseModel):
    total_orders: int
    total_revenue: float
    average_order_value: float
    top_selling_items: List[dict]

# COGS Schemas
class COGSBase(BaseModel):
    week_start_date: datetime
    week_end_date: datetime
    amount: float
    
    @validator('amount')
    def validate_positive_amount(cls, v):
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v

class COGSCreate(COGSBase):
    pass

class COGSUpdate(BaseModel):
    amount: float
    
    @validator('amount')
    def validate_positive_amount(cls, v):
        if v < 0:
            raise ValueError('Amount must be non-negative')
        return v

class COGS(COGSBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)

# Action Item Schemas
class ActionItemBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "medium"  # low, medium, high
    status: str = "pending"  # pending, in_progress, completed
    action_type: str = "other"  # integration, data_entry, analysis, configuration, other
    
    @validator('priority')
    def validate_priority(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError('Priority must be one of: low, medium, high')
        return v
        
    @validator('status')
    def validate_status(cls, v):
        if v not in ["pending", "in_progress", "completed"]:
            raise ValueError('Status must be one of: pending, in_progress, completed')
        return v
        
    @validator('action_type')
    def validate_action_type(cls, v):
        if v not in ["integration", "data_entry", "analysis", "configuration", "other"]:
            raise ValueError('Action type must be one of: integration, data_entry, analysis, configuration, other')
        return v

class ActionItemCreate(ActionItemBase):
    pass

class ActionItemUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    action_type: Optional[str] = None
    
    @validator('priority')
    def validate_priority(cls, v):
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError('Priority must be one of: low, medium, high')
        return v
        
    @validator('status')
    def validate_status(cls, v):
        if v is not None and v not in ["pending", "in_progress", "completed"]:
            raise ValueError('Status must be one of: pending, in_progress, completed')
        return v
        
    @validator('action_type')
    def validate_action_type(cls, v):
        if v is not None and v not in ["integration", "data_entry", "analysis", "configuration", "other"]:
            raise ValueError('Action type must be one of: integration, data_entry, analysis, configuration, other')
        return v

class ActionItem(ActionItemBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, arbitrary_types_allowed=True)
