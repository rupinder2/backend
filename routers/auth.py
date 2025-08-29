from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from typing import Dict, Any
from auth import get_current_user, get_current_user_id, validate_token_only
from models import UserResponse, TokenValidationResponse
from supabase_client import get_get_supabase_admin()

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/validate-token", response_model=TokenValidationResponse)
async def validate_token(
    token_payload: Dict[str, Any] = Depends(validate_token_only)
) -> TokenValidationResponse:
    """
    Validate JWT token and return user information
    
    Returns:
        TokenValidationResponse with validation status and user data
    """
    try:
        user_data = UserResponse(
            user_id=token_payload.get('sub', ''),
            email=token_payload.get('email', ''),
            role=token_payload.get('role', ''),
            is_anonymous=token_payload.get('is_anonymous', False),
            session_id=token_payload.get('session_id'),
            app_metadata=token_payload.get('app_metadata', {}),
            user_metadata=token_payload.get('user_metadata', {}),
            expires_at=token_payload.get('exp')
        )
        
        return TokenValidationResponse(
            valid=True,
            user=user_data,
            message="Token is valid"
        )
    except Exception as e:
        return TokenValidationResponse(
            valid=False,
            user=None,
            message=f"Token validation failed: {str(e)}"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> UserResponse:
    """
    Get current authenticated user information
    
    Returns:
        UserResponse with current user data
    """
    return UserResponse(
        user_id=current_user['user_id'],
        email=current_user['email'],
        role=current_user['role'],
        is_anonymous=current_user['is_anonymous'],
        session_id=current_user.get('session_id'),
        app_metadata=current_user.get('app_metadata', {}),
        user_metadata=current_user.get('user_metadata', {}),
        expires_at=current_user.get('expires_at')
    )

@router.get("/profile")
async def get_user_profile(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, Any]:
    """
    Get detailed user profile from Supabase
    
    Returns:
        User profile data from Supabase auth users table
    """
    try:
        # Get user details from Supabase auth
        user_response = get_supabase_admin().auth.admin.get_user_by_id(user_id)
        
        if user_response.user:
            return {
                "user_id": user_response.user.id,
                "email": user_response.user.email,
                "created_at": user_response.user.created_at,
                "last_sign_in_at": user_response.user.last_sign_in_at,
                "user_metadata": user_response.user.user_metadata or {},
                "app_metadata": user_response.user.app_metadata or {}
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user profile: {str(e)}"
        )

@router.post("/logout")
async def logout_user(
    user_id: str = Depends(get_current_user_id)
) -> Dict[str, str]:
    """
    Logout user (invalidate session)
    Note: This endpoint logs the action but actual token invalidation 
    happens on the client side by removing the token
    
    Returns:
        Success message
    """
    try:
        # In a real-world scenario, you might want to:
        # 1. Add the token to a blacklist
        # 2. Log the logout event
        # 3. Clear any server-side session data
        
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )
