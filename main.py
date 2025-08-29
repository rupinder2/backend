from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from config import settings
from routers import auth_router
from routers.books import router as books_router

# Validate configuration on startup
try:
    settings.validate()
except ValueError as e:
    print(f"Configuration error: {e}")
    exit(1)

# Initialize FastAPI app
app = FastAPI(
    title="Library Management System API",
    description="FastAPI backend for Mini Library Management System with Supabase authentication",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
allowed_origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "https://front-end-delta-lac-93.vercel.app",
    "*"  # Allow all origins for now
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(books_router, prefix="/api")

# Also include routers without /api prefix for direct access
app.include_router(auth_router, prefix="", tags=["Auth Direct"])
app.include_router(books_router, prefix="", tags=["Books Direct"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Library Management System API",
        "version": "1.0.0",
        "docs": "/docs",
        "features": ["Book Management", "Check-in/Check-out", "Search", "AI Recommendations"]
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="info"
    )