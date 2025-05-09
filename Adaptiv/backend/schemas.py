from pydantic import BaseModel, EmailStr, Field
from typing import Optional
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
