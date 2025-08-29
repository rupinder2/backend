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
5. **Lazy Loading**: Supabase clients are initialized lazily to avoid serverless issues

## Files Modified for Vercel Deployment

- `vercel.json` - Vercel configuration (simplified)
- `requirements.txt` - Fixed dependency versions, added `mangum`
- `main.py` - Added Mangum handler and improved CORS + graceful config validation
- `supabase_client.py` - **FIXED**: Lazy initialization to prevent module-level errors
- `config.py` - Enhanced environment detection and validation
- `routers/*.py` - Updated to use lazy Supabase client functions

## Recent Fixes Applied

✅ **Fixed Supabase Client Error**: Replaced module-level initialization with lazy loading  
✅ **Fixed Dependency Versions**: Pinned compatible versions for Vercel  
✅ **Fixed JWT Import Error**: Replaced `jwt` with `PyJWT` package  
✅ **Fixed Vercel Handler Error**: Moved handler to `api/index.py` with proper structure  
✅ **Improved Error Handling**: Graceful config validation for Vercel environment  
✅ **Enhanced CORS**: Better handling of Vercel preview URLs  

## Troubleshooting

1. **Build Fails**: Check that all dependencies are in requirements.txt with correct versions
2. **Environment Variables**: Ensure all required env vars are set in Vercel dashboard
3. **CORS Issues**: Frontend URL should be added to FRONTEND_URL env var
4. **Supabase Connection**: Test /health endpoint to verify Supabase configuration
5. **Import Errors**: All imports now use lazy initialization to prevent serverless issues

## Quick Deploy Script

Run the deployment script:
```bash
chmod +x deploy.sh
./deploy.sh
```
