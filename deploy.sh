#!/bin/bash

# Deploy FastAPI Backend to Vercel
echo "🚀 Deploying FastAPI Backend to Vercel..."

# Check if vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "❌ Vercel CLI not found. Installing..."
    npm install -g vercel
fi

# Deploy to production
echo "📦 Deploying to production..."
vercel --prod

echo "✅ Deployment complete!"
echo ""
echo "📝 Don't forget to set your environment variables in Vercel dashboard:"
echo "   - SUPABASE_URL"
echo "   - SUPABASE_SERVICE_ROLE_KEY"
echo "   - SUPABASE_ANON_KEY"
echo "   - SUPABASE_JWT_SECRET"
echo ""
echo "🔗 You can set them at: https://vercel.com/dashboard"
