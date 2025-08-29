from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    
class UserResponse(BaseModel):
    """User response model"""
    user_id: str
    email: str
    role: str
    is_anonymous: bool
    session_id: Optional[str] = None
    app_metadata: Dict[str, Any] = {}
    user_metadata: Dict[str, Any] = {}
    expires_at: Optional[int] = None
    
class UserProfile(BaseModel):
    """User profile model"""
    user_id: str
    email: str
    created_at: Optional[datetime] = None
    last_sign_in_at: Optional[datetime] = None
    user_metadata: Dict[str, Any] = {}
    
class TokenValidationResponse(BaseModel):
    """Token validation response model"""
    valid: bool
    user: Optional[UserResponse] = None
    message: str
