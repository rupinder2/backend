# Deploy FastAPI Backend to Vercel

## Prerequisites
1. Install Vercel CLI: `npm install -g vercel`
2. Login to Vercel: `vercel login`

## Deployment Steps

### 1. Deploy from Backend Directory
```bash
cd backend
vercel --prod
```

### 2. Set Environment Variables in Vercel Dashboard
Go to your Vercel project settings and add these environment variables:

**Required Variables:**
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Your Supabase service role key
- `SUPABASE_ANON_KEY` - Your Supabase anonymous key
- `SUPABASE_JWT_SECRET` - Your Supabase JWT secret

**Optional Variables:**
- `FRONTEND_URL` - Your frontend deployment URL (will be set after frontend deployment)

### 3. Alternative: Deploy with CLI Environment Variables
```bash
vercel --prod \
  -e SUPABASE_URL="your_supabase_url" \
  -e SUPABASE_SERVICE_ROLE_KEY="your_service_role_key" \
  -e SUPABASE_ANON_KEY="your_anon_key" \
  -e SUPABASE_JWT_SECRET="your_jwt_secret"
```

### 4. Test Deployment
After deployment, test these endpoints:
- `https://your-backend-url.vercel.app/` - Root endpoint
- `https://your-backend-url.vercel.app/health` - Health check
- `https://your-backend-url.vercel.app/docs` - API documentation

## Important Notes

1. **Serverless Functions**: Your FastAPI app runs as serverless functions on Vercel
2. **Cold Starts**: First request might be slower due to cold start
3. **File Uploads**: Large file uploads might timeout (15s limit for Hobby plan)
4. **CORS**: Configured to allow Vercel preview URLs automatically

## Files Added for Vercel Deployment

- `vercel.json` - Vercel configuration
- `requirements.txt` - Updated with `mangum` for ASGI compatibility
- `main.py` - Updated with Mangum handler and improved CORS

## Troubleshooting

1. **Build Fails**: Check that all dependencies are in requirements.txt
2. **Environment Variables**: Ensure all required env vars are set in Vercel dashboard
3. **CORS Issues**: Frontend URL should be added to FRONTEND_URL env var
4. **Supabase Connection**: Test /health endpoint to verify Supabase configuration
