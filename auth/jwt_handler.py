import jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from config import settings

class JWTHandler:
    """Handle JWT token validation and extraction"""
    
    def __init__(self):
        self.secret = settings.SUPABASE_JWT_SECRET
        self.algorithm = "HS256"
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decode and validate a Supabase JWT token
        
        Args:
            token: The JWT token to decode
            
        Returns:
            Dict containing the decoded token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Decode the token
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=["authenticated", "anon"],  # Accept both authenticated and anonymous tokens
                options={"verify_exp": True}
            )
            
            
            # Validate token expiration
            exp = payload.get('exp')
            if exp:
                exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
                if exp_datetime < datetime.now(timezone.utc):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Token has expired"
                    )
            
            return payload
            
        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token validation failed: {str(e)}"
            )
    
    def extract_user_id(self, token: str) -> str:
        """
        Extract user ID from JWT token
        
        Args:
            token: The JWT token
            
        Returns:
            The user ID (sub claim)
        """
        payload = self.decode_token(token)
        user_id = payload.get('sub')
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID"
            )
        
        return user_id
    
    def extract_user_email(self, token: str) -> str:
        """
        Extract user email from JWT token
        
        Args:
            token: The JWT token
            
        Returns:
            The user email
        """
        payload = self.decode_token(token)
        email = payload.get('email')
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing email"
            )
        
        return email
    
    def validate_user_role(self, token: str, required_role: str = "authenticated") -> bool:
        """
        Validate user role from JWT token
        
        Args:
            token: The JWT token
            required_role: The required role (default: "authenticated")
            
        Returns:
            True if user has required role
        """
        payload = self.decode_token(token)
        user_role = payload.get('role')
        
        if user_role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}"
            )
        
        return True
    
    def get_user_metadata(self, token: str) -> Dict[str, Any]:
        """
        Extract user metadata from JWT token
        
        Args:
            token: The JWT token
            
        Returns:
            Dictionary containing user metadata
        """
        payload = self.decode_token(token)
        
        return {
            "user_id": payload.get('sub'),
            "email": payload.get('email'),
            "role": payload.get('role'),
            "aal": payload.get('aal'),  # Authentication Assurance Level
            "session_id": payload.get('session_id'),
            "is_anonymous": payload.get('is_anonymous', False),
            "app_metadata": payload.get('app_metadata', {}),
            "user_metadata": payload.get('user_metadata', {}),
            "expires_at": payload.get('exp')
        }

# Initialize JWT handler
jwt_handler = JWTHandler()
