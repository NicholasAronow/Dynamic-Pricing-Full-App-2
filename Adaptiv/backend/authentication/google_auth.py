import os
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
import json

from database import get_db
import models, schemas
from routers.auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

# Create router
google_auth_router = APIRouter()

# Get the Google Client ID from environment variables
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
if not GOOGLE_CLIENT_ID:
    print("Warning: GOOGLE_CLIENT_ID not set in environment variables")

# Route to handle Google authentication callback
@google_auth_router.post("/google-auth")
async def google_auth(request: Request, db: Session = Depends(get_db)):
    # Get the request body as JSON
    try:
        body = await request.json()
        id_token_jwt = body.get("credential")
        
        print(f"Received Google auth request with token: {id_token_jwt[:20]}...")
        
        if not id_token_jwt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Missing Google ID token"
            )
            
        # Verify the token
        try:
            print(f"Verifying Google token with CLIENT_ID: {GOOGLE_CLIENT_ID[:10]}...")
            if not GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Google Client ID not configured on server"
                )
                
            idinfo = id_token.verify_oauth2_token(
                id_token_jwt, requests.Request(), GOOGLE_CLIENT_ID
            )
            
            print(f"Google token verified successfully. User info: {idinfo.get('email')}, {idinfo.get('name')}")
            
            # Extract user info from the token
            email = idinfo.get("email")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email not found in Google token"
                )
                
            # Check if user exists
            user = db.query(models.User).filter(models.User.email == email).first()
            
            if not user:
                # Create new user
                user = models.User(
                    email=email,
                    name=idinfo.get("name", ""),
                    # Setting empty password hash as they're using Google auth
                    hashed_password="",  
                    is_google_user=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            # Generate JWT token
            access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user.email, "user_id": user.id}, 
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token, 
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name
                }
            }
            
        except ValueError:
            # Invalid token
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token"
            )
            
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request body"
        )
