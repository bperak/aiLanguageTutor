# Frontend Environment Setup

## Environment Variables

To fix the "Failed to fetch" error, you need to create a `.env.local` file in the frontend directory with the following content:

```bash
# Frontend Environment Variables
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Steps to Fix the Issue

1. Create a file named `.env.local` in the `frontend/` directory
2. Add the content above to the file
3. Restart the Next.js development server

## Alternative: Manual Configuration

If you prefer not to use environment variables, you can modify the `LexicalGraph3D.tsx` component directly by changing line 127:

```typescript
const apiBase = "http://localhost:8000"; // Hardcoded for development
```

## Verification

After setting up the environment variables:

1. Open the browser console
2. Navigate to the lexical graph page
3. Check the console logs for environment variable information
4. Use the "API Connection Test" component to verify the connection

## Common Issues

- **Backend not running**: Make sure the backend is running on port 8000
- **CORS errors**: The backend should be configured to allow requests from localhost:3000
- **Network issues**: Check if localhost:8000 is accessible from your browser
