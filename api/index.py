from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Create FastAPI app
app = FastAPI(
    title="Email OTP Authentication API",
    description="FastAPI backend with Supabase email OTP authentication",
    version="1.0.0"
)

# Basic CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Be permissive for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI is working on Vercel!",
        "version": "1.0.0",
        "environment": "vercel" if os.getenv("VERCEL") else "local"
    }

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy", "platform": "vercel"}

@app.get("/test")
async def test():
    """Test endpoint"""
    return {"test": "success", "message": "API is responding correctly"}
