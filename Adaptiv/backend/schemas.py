from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
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

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

# Complete User with Profile
class UserWithProfile(User):
    business: Optional[BusinessProfile] = None
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

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
    
    class Config:
        orm_mode = True

# Order Analytics Response
class OrderAnalytics(BaseModel):
    total_orders: int
    total_revenue: float
    average_order_value: float
    top_selling_items: List[dict]
