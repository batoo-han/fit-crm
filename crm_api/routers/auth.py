"""Authentication router."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from database.db import get_db_session
from database.models_crm import User
from crm_api.dependencies import create_access_token, security, get_current_user
from datetime import timedelta
import bcrypt
from loguru import logger

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db_session)):
    """Login endpoint."""
    logger.info(f"Login attempt for username: {credentials.username}")
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user:
        logger.warning(f"User not found: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    if not user.is_active:
        logger.warning(f"User is inactive: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Check password
    try:
        password_valid = bcrypt.checkpw(
            credentials.password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        )
        if not password_valid:
            logger.warning(f"Invalid password for user: {credentials.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
            )
    except Exception as e:
        logger.error(f"Error checking password: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30 * 24 * 60)  # 30 days
    access_token = create_access_token(
        data={"sub": str(user.id)},  # JWT subject must be a string
        expires_delta=access_token_expires
    )
    
    logger.info(f"Login successful for user: {credentials.username} (ID: {user.id})")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active
        }
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return {"message": "Logged out successfully"}

