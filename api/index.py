"""
Vercel serverless function entry point
"""
from mangum import Mangum
import sys
import os

# Add the parent directory to the path so we can import from the root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

# Create the handler for Vercel
handler = Mangum(app, lifespan="off")
