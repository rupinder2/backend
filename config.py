import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
    SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
    
    # API Configuration
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", os.getenv("PORT", "8000")))
    
    # CORS Configuration - Handle Vercel deployment URLs
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Environment detection
    IS_VERCEL = os.getenv("VERCEL") == "1"
    IS_PRODUCTION = os.getenv("VERCEL_ENV") == "production"
    
    def validate(self):
        """Validate that all required environment variables are set"""
        required_vars = [
            "SUPABASE_URL", 
            "SUPABASE_SERVICE_ROLE_KEY", 
            "SUPABASE_ANON_KEY",
            "SUPABASE_JWT_SECRET"
        ]
        
        missing_vars = []
        for var in required_vars:
            value = getattr(self, var)
            if not value or value.strip() == "":
                missing_vars.append(var)
        
        if missing_vars:
            if self.IS_VERCEL:
                print(f"Warning: Missing environment variables in Vercel: {', '.join(missing_vars)}")
                print("Please set these in your Vercel project settings")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

settings = Settings()
