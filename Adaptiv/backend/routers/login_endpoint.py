"""
Add a custom login endpoint to match frontend expectations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict
from datetime import timedelta
from database import get_db
import models
from .auth import authenticate_user, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

login_router = APIRouter()

@login_router.post("/login")
async def login(credentials: Dict[str, str], db: Session = Depends(get_db)):
    """
    Custom login endpoint that matches the frontend's expected format
    """
    email = credentials.get("email", "")
    password = credentials.get("password", "")
    
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate the access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        },
        expires_delta=access_token_expires
    )
    
    # Return token in format expected by frontend
    return {"token": token, "access_token": token, "token_type": "bearer"}


@login_router.post("/token")
async def login_with_form(form_data: Dict[str, str], db: Session = Depends(get_db)):
    """
    Alternate login endpoint that accepts form data
    """
    email = form_data.get("username", form_data.get("email", ""))
    password = form_data.get("password", "")
    
    user = authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Generate the access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id
        },
        expires_delta=access_token_expires
    )
    
    # Return token in both formats for compatibility
    return {"token": token, "access_token": token, "token_type": "bearer"}
