# AutoPost 🚀

AutoPost is a dual-platform scheduling and automation system built with Django. It allows users to schedule Images and Reels for **Instagram** as well as Videos for **YouTube (with full metadata like Tags, Categories, and Privacy)**. 

The system leverages a background task processor (APScheduler) to automatically push media to connected accounts at the exact scheduled local time.

---

## 🌟 Key Features
- **Multi-Account Support**: Manage multiple Instagram and YouTube accounts from one dashboard.
- **Cross-Platform Scheduling**: Create instances of the same Reel/Video that post to Instagram and YouTube simultaneously.
- **YouTube Advanced Metadata**: Apply COPPA requirements, Privacy settings (e.g. Unlisted, Private delay), specific tags, and YouTube standard categories.
- **Background Processing**: Reliable background execution using `APScheduler`. No external Redis/Celery required.
- **UI Architecture**: Premium neumorphic dual-mode (Light ☀️ / Dark 🌙) interface designed for ease of use.
- **Auto Token Refresh**: Securely stores and automatically refreshes Google OAuth tokens.

---

## 🛠️ Prerequisites & Setup

Ensure you have Python 3.10+ installed.

1. **Clone the repository and enter the directory:**
2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Mac/Linux
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```
5. **Run the server:**
   ```bash
   python manage.py runserver
   ```
   *(Note: The background scheduler automatically starts with the Django app).*

---

## 🔑 Environment Variables (`.env`)
Create a `.env` file in your root folder with the following variables:

```env
# Required for YouTube OAuth Desktop integration
GOOGLE_OAUTH2_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_OAUTH2_CLIENT_SECRET=your_google_client_secret

# Disable HTTPS requirement for OAuth during local development
OAUTHLIB_INSECURE_TRANSPORT=1
OAUTHLIB_RELAX_TOKEN_SCOPE=1
```

---

## 📱 How to Setup Instagram Accounts

Instagram integration uses the **Instagram Graph API**. You will need a **Facebook Page** linked to a **Professional Instagram Account**.

### Step 1: Create a Meta App
1. Go to the [Meta Developer Portal](https://developers.facebook.com/).
2. Click **Create App** → Select **Other** → **Business**.
3. Name your app and create it.
4. On the Add Products page, setup **Instagram Graph API**.

### Step 2: Generate the Access Token
1. Go to **Tools** → **Graph API Explorer**.
2. Select your App on the right side.
3. Under Permissions, add: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`.
4. Click **Generate Access Token**. Approve the popup linking your Facebook Page.
5. *(Optional but Recommended):* By default, this token lasts 1-2 hours. To generate a long-lived (60 day) token, click the **(i)** info icon next to your token to open the Access Token Tool. Click **Extend Access Token** at the bottom.

### Step 3: Find your Instagram User ID
1. Still in the Graph API Explorer, hit this endpoint: `GET /me/accounts?fields=instagram_business_account`
2. You will get a JSON response. Look for the `instagram_business_account: { id: "178414XXXXXXX" }`. That number is your Instagram User ID.

### Step 4: Add to AutoPost
1. Open AutoPost in your browser (`http://localhost:8000`).
2. Go to **Accounts** → **Connect Instagram**.
3. Enter a friendly name, the `Instagram User ID`, and the `Access Token` you just generated.

---

## 📺 How to Setup YouTube Accounts

YouTube integration uses standard **Google OAuth 2.0**. Because AutoPost runs locally right now, you need to configure a "Desktop App" OAuth client.

### Step 1: Enable YouTube API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new Project (or select an existing one).
3. Go to **APIs & Services** → **Library**.
4. Search for "**YouTube Data API v3**" and click **Enable**.

### Step 2: Configure OAuth Screen
1. Go to **APIs & Services** → **OAuth consent screen**.
2. Select **External** (unless you only want Google Workspace users).
3. Fill out the required App Name and Support Email fields natively.
4. Skip Scopes (AutoPost requests them automatically). Add your personal Google account under **Test Users**.

### Step 3: Create OAuth Credentials
1. Go to **APIs & Services** → **Credentials**.
2. Click **Create Credentials** → **OAuth client ID**.
3. For Application Type, select **Desktop app** (or Installed app).
4. *(If Desktop app doesn't ask for a redirect URI, that is fine. If it asks or if you choose Web App instead, you MUST add `http://localhost:8000/accounts/youtube/callback/` to Authorized Redirect URIs).*
5. Click **Create**.
6. You will receive a **Client ID** and a **Client Secret**. Add these to your `.env` file as shown above.

### Step 4: Connect via AutoPost
1. Open AutoPost (`http://localhost:8000`).
2. Go to **Accounts** → **Connect YouTube**.
3. You will be redirected to Google to log in. Check the boxes that ask for permission to "Manage your YouTube Account" and click Continue.
4. AutoPost will capture your Refresh Token allowing the app to post videos without forcing you to log in ever again!
