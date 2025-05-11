"""
Add a custom register endpoint to match frontend expectations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict
from datetime import timedelta
from database import get_db
import models
from auth import get_user, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

register_router = APIRouter()

@register_router.post("/register")
async def register(credentials: Dict[str, str], db: Session = Depends(get_db)):
    """
    Custom register endpoint that matches the frontend's expected format
    """
    email = credentials.get("email", "")
    password = credentials.get("password", "")
    
    # Validate input
    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required"
        )
    
    # Check if user already exists
    db_user = get_user(db, email=email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    db_user = models.User(email=email, hashed_password=hashed_password)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Generate access token for the new user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": db_user.email,
            "user_id": db_user.id
        },
        expires_delta=access_token_expires
    )
    
    # Return token in format expected by frontend
    return {"token": token}
