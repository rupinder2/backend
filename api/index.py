from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys

# Add parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Try to import our modules with fallback
try:
    from config import settings
    from routers import auth_router
    from routers.documents import router as documents_router
    modules_loaded = True
except ImportError as e:
    print(f"Import error: {e}")
    # Create minimal settings for fallback
    class FallbackSettings:
        SUPABASE_URL = os.getenv("SUPABASE_URL", "")
        SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")
        FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
        IS_VERCEL = os.getenv("VERCEL") == "1"
    settings = FallbackSettings()
    auth_router = None
    documents_router = None
    modules_loaded = False

# Initialize FastAPI app
app = FastAPI(
    title="Email OTP Authentication API",
    description="FastAPI backend with Supabase email OTP authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for production and development
allowed_origins = [
    "http://localhost:3000",  # Local development
    "https://localhost:3000", # Local development with SSL
]

# Add production frontend URL if available
if hasattr(settings, 'FRONTEND_URL') and settings.FRONTEND_URL:
    allowed_origins.append(settings.FRONTEND_URL)

# For Vercel deployments, allow Vercel preview URLs
if os.getenv("VERCEL"):
    allowed_origins.extend([
        "https://*.vercel.app",
        "https://*.vercel.sh"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins + ["*"],  # Be permissive for now
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers (only if successfully imported)
if modules_loaded and auth_router:
    app.include_router(auth_router, prefix="/api")
if modules_loaded and documents_router:
    app.include_router(documents_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Email OTP Authentication API",
        "version": "1.0.0",
        "docs": "/docs",
        "modules_loaded": modules_loaded,
        "environment": "vercel" if os.getenv("VERCEL") else "local"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return {
            "status": "healthy",
            "modules_loaded": modules_loaded,
            "supabase_configured": bool(getattr(settings, 'SUPABASE_URL', None) and getattr(settings, 'SUPABASE_JWT_SECRET', None)),
            "platform": "vercel"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )

@app.get("/test")
async def test():
    """Test endpoint"""
    return {
        "test": "success", 
        "message": "API is responding correctly",
        "modules_loaded": modules_loaded
    }

# Fallback endpoints if modules couldn't be loaded
if not modules_loaded:
    @app.get("/api/documents")
    async def fallback_documents():
        return JSONResponse(
            status_code=503,
            content={"error": "Backend modules not loaded. Please check environment variables."}
        )
    
    @app.post("/api/documents/upload")
    async def fallback_upload():
        return JSONResponse(
            status_code=503,
            content={"error": "Backend modules not loaded. Please check environment variables."}
        )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint not found", "path": str(request.url)}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )
