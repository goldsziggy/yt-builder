# YouTube Upload Integration

The YouTube Video Builder includes integration to upload completed videos directly to YouTube.

## Setup Instructions

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **YouTube Data API v3**:
   - Go to "APIs & Services" > "Library"
   - Search for "YouTube Data API v3"
   - Click "Enable"

### 2. Create OAuth Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Configure the OAuth consent screen if prompted:
   - User Type: External (for personal use) or Internal (for organization)
   - Add app name, user support email, developer contact
   - Add scopes: `https://www.googleapis.com/auth/youtube.upload`
   - Add test users (your email) if in testing mode
4. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: "YT Video Builder" (or your preference)
   - Authorized redirect URIs: Add `http://localhost:5000/api/youtube/auth/callback`
     - For production, add your domain: `https://yourdomain.com/api/youtube/auth/callback`
5. Download the JSON file

### 3. Configure the Application

1. Rename the downloaded JSON file to `client_secrets.json`
2. Place it in the `secrets/` directory of the project

**Example `client_secrets.json` structure:**
```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["http://localhost:5000/api/youtube/auth/callback"]
  }
}
```

### 4. Optional: Custom Client Secrets Location

You can specify a custom location for the client secrets file using an environment variable:

```bash
export YOUTUBE_CLIENT_SECRETS=/path/to/your/client_secrets.json
```

Or in Docker:
```yaml
environment:
  YOUTUBE_CLIENT_SECRETS: /app/config/client_secrets.json
```

## Usage

### Web Interface

1. **Complete a Video Build**
   - Create and run a video build job
   - Wait for the job to complete

2. **Upload to YouTube**
   - Click the "📺 YouTube" button on the completed job
   - First time: Click "Authenticate with YouTube"
   - Sign in with your Google account
   - Grant permissions to upload videos
   - Fill in video details:
     - **Title**: Video title (required, max 100 characters)
     - **Description**: Video description (optional)
     - **Privacy**: Private, Unlisted, or Public
     - **Tags**: Comma-separated tags (optional)
     - **Category**: Video category
   - Click "Upload to YouTube"
   - Wait for upload to complete
   - Get the YouTube video URL

### API Usage

**1. Check Authentication Status**
```bash
GET /api/youtube/auth/status

Response:
{
  "authenticated": true,
  "youtube_available": true
}
```

**2. Get OAuth URL (if not authenticated)**
```bash
GET /api/youtube/auth/url

Response:
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?..."
}
```

**3. Upload Video**
```bash
POST /api/jobs/{job_id}/youtube/upload
Content-Type: application/json

{
  "title": "My Awesome Video",
  "description": "Created with YT Video Builder",
  "privacy": "private",
  "tags": ["video", "builder", "automated"],
  "category": "22"
}

Response:
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "message": "Video uploaded successfully!"
}
```

## YouTube Categories

Common category IDs:
- `1` - Film & Animation
- `2` - Autos & Vehicles
- `10` - Music
- `15` - Pets & Animals
- `17` - Sports
- `19` - Travel & Events
- `20` - Gaming
- `22` - People & Blogs (default)
- `23` - Comedy
- `24` - Entertainment
- `25` - News & Politics
- `26` - Howto & Style
- `27` - Education
- `28` - Science & Technology

## Privacy Settings

- **private**: Only you can see the video
- **unlisted**: Anyone with the link can see the video (won't appear in search)
- **public**: Everyone can see the video

## Troubleshooting

### "YouTube OAuth not configured"

**Cause**: `secrets/client_secrets.json` file not found

**Solution**: Create the file in the `secrets/` directory with your OAuth credentials

### "YouTube API not available"

**Cause**: Required Python packages not installed

**Solution**:
```bash
pip install -r requirements.txt
```

### "Not authenticated with YouTube"

**Cause**: OAuth authentication not completed or expired

**Solution**: Click "Authenticate with YouTube" button and complete the OAuth flow

### "Upload failed: Quota exceeded"

**Cause**: YouTube API quota limit reached

**Solution**:
- Wait 24 hours for quota to reset
- Request quota increase from Google Cloud Console
- Each upload costs ~1600 quota units
- Default quota: 10,000 units/day (~6 uploads/day)

### OAuth Callback Not Working

**Cause**: Redirect URI mismatch

**Solution**:
1. Check that the redirect URI in Google Cloud Console matches exactly: `http://localhost:5000/api/youtube/auth/callback`
2. For production, use your actual domain
3. Ensure there are no extra slashes or different ports

## Security Considerations

1. **Keep `secrets/client_secrets.json` private**: Never commit to version control
2. **The `secrets/` directory is already in `.gitignore`**: All files in this directory are automatically ignored
3. **Use environment variables** for production deployments
4. **Limit OAuth scopes**: Only use `youtube.upload` scope (not `youtube` which has broader access)
5. **Test users**: In OAuth consent screen testing mode, only authorized test users can authenticate
6. **Publish your app**: To allow any user to authenticate, publish your OAuth consent screen (requires verification for sensitive scopes)

## Quota Management

YouTube API has daily quota limits:
- Default: 10,000 units/day
- Video upload: ~1,600 units
- Estimated uploads: ~6 per day

To request quota increase:
1. Go to Google Cloud Console
2. Navigate to "APIs & Services" > "Quotas"
3. Find "YouTube Data API v3"
4. Request quota increase (requires justification)

## Production Deployment

For production use:

1. **Use HTTPS** for redirect URIs
2. **Configure proper domain** in OAuth credentials
3. **Store credentials securely** (use secrets management)
4. **Enable session persistence** (use database-backed sessions instead of memory)
5. **Handle token refresh** (implement token refresh logic for long-lived sessions)
6. **Add logging** for upload tracking and debugging
7. **Implement rate limiting** to stay within API quota

## Example Production Environment Variables

```bash
# YouTube OAuth
YOUTUBE_CLIENT_SECRETS=/etc/yt-builder/client_secrets.json

# Flask session (use a random secret key)
SECRET_KEY=your-production-secret-key-here

# Server configuration
PORT=5000
DEBUG=false
```

## Additional Resources

- [YouTube Data API Documentation](https://developers.google.com/youtube/v3)
- [OAuth 2.0 for Web Server Applications](https://developers.google.com/identity/protocols/oauth2/web-server)
- [YouTube API Quota Calculator](https://developers.google.com/youtube/v3/determine_quota_cost)
