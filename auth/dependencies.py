from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from .jwt_handler import jwt_handler

# Security scheme for JWT Bearer token
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Dictionary containing user metadata
        
    Raises:
        HTTPException: If token is invalid or user is not authenticated
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required"
        )
    
    # Validate token and extract user metadata
    user_metadata = jwt_handler.get_user_metadata(credentials.credentials)
    
    # Ensure user is authenticated (not anonymous)
    if user_metadata.get('is_anonymous', False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Anonymous users not allowed"
        )
    
    return user_metadata

async def get_current_user_id(
    user_metadata: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Dependency to get current user ID
    
    Args:
        user_metadata: User metadata from get_current_user dependency
        
    Returns:
        User ID string
    """
    return user_metadata['user_id']

async def get_current_user_email(
    user_metadata: Dict[str, Any] = Depends(get_current_user)
) -> str:
    """
    Dependency to get current user email
    
    Args:
        user_metadata: User metadata from get_current_user dependency
        
    Returns:
        User email string
    """
    return user_metadata['email']

async def validate_token_only(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to validate JWT token without additional checks
    Useful for endpoints that need to support both authenticated and anonymous users
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        Dictionary containing token payload
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required"
        )
    
    return jwt_handler.decode_token(credentials.credentials)
