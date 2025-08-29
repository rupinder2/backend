from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
from config import settings
from routers import auth_router
from routers.documents import router as documents_router
from mangum import Mangum

# Validate configuration on startup (but be graceful for Vercel)
try:
    settings.validate()
except ValueError as e:
    if settings.IS_VERCEL:
        print(f"Configuration warning in Vercel: {e}")
        print("The app may not work properly until environment variables are set")
    else:
        print(f"Configuration error: {e}")
        exit(1)

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
if settings.FRONTEND_URL:
    allowed_origins.append(settings.FRONTEND_URL)

# For Vercel deployments, allow Vercel preview URLs
if os.getenv("VERCEL"):
    allowed_origins.extend([
        "https://*.vercel.app",
        "https://*.vercel.sh"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(documents_router, prefix="/api")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Email OTP Authentication API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health check - could be expanded to check database connectivity
        return {
            "status": "healthy",
            "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_JWT_SECRET)
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy", 
                "error": str(e)
            }
        )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={"message": "Endpoint not found"}
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error"}
    )

# Vercel serverless function handler
from mangum import Mangum
handler = Mangum(app, lifespan="off")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )
