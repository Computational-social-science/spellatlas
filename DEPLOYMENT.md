# SpellAtlas Deployment Guide

This guide describes how to deploy the SpellAtlas application using **Vercel** (Frontend) and **Render** (Backend). This architecture is cost-effective (free tiers available) and scalable.

## Prerequisites

1.  **GitHub Repository**: Ensure your code is pushed to a GitHub repository.
2.  **Vercel Account**: Sign up at [vercel.com](https://vercel.com).
3.  **Render Account**: Sign up at [render.com](https://render.com).

---

## Part 1: Backend Deployment (Render)

We will deploy the backend first to obtain the API URL.

1.  **New Web Service**:
    -   Log in to Render dashboard.
    -   Click **New +** -> **Web Service**.
    -   Connect your GitHub repository.

2.  **Configuration**:
    -   **Name**: `spellatlas-backend` (or similar)
    -   **Language/Runtime**: `Docker`
    -   **Root Directory**: `.` (Leave default)
        -   *Important*: Do NOT set this to `backend`. We need the root context to access the `data/` folder.
    -   **Dockerfile Path**: `backend/Dockerfile`
    -   **Region**: Choose one close to you (e.g., Singapore, Oregon).
    -   **Instance Type**: Free (if available) or Starter.

3.  **Environment Variables**:
    -   Add the following variable:
        -   `ALLOWED_ORIGINS`: `*` (Initially allow all, later update to your Vercel URL).

4.  **Deploy**:
    -   Click **Create Web Service**.
    -   Wait for the build to finish.
    -   **Copy the URL**: You will see a URL like `https://spellatlas-backend.onrender.com`. Save this.

### Data Persistence Note
On the free tier, the disk is ephemeral. The database (`stats.db`) will reset on redeployment.
-   **Initial Data**: The app will start empty.
-   **Populating Data**: You can add a **Cron Job** in Render (requires payment) or manually run the fetch script locally and commit a `detected_errors.json` (requires modifying `.gitignore` to un-ignore it).
-   *Recommendation for Free Tier*: Just accept that data resets on deploy for now.

---

## 5. Database Setup (Supabase) - Recommended

To ensure data persistence (prevent data loss on restart), we will use Supabase (PostgreSQL).

1.  **Create Project**:
    -   Go to [Supabase](https://supabase.com/) and create a new project.
    -   Set a strong database password.
    -   Wait for the project to initialize.

2.  **Get Connection String**:
    -   Go to **Project Settings** -> **Database**.
    -   Under **Connection string**, select **URI**.
    -   Copy the string. It looks like: `postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres`

3.  **Configure Render**:
    -   Go to your Render Dashboard -> Select `spellatlas-backend`.
    -   Click **Environment**.
    -   Add a new Environment Variable:
        -   **Key**: `DATABASE_URL`
        -   **Value**: Paste your Supabase connection string (Replace `[YOUR-PASSWORD]` with your actual password).
    -   Click **Save Changes**.

4.  **Verify**:
    -   Render will automatically redeploy (or you can trigger a manual deploy).
    -   Check the logs. You should see: `Using PostgreSQL database.`
    -   The application will automatically create the necessary tables and import existing data from `detected_errors.json` if the database is empty.

## 6. Frontend Deployment (Vercel)

1.  **New Project**:
    -   Log in to Vercel dashboard.
    -   Click **Add New...** -> **Project**.
    -   Import your GitHub repository.

2.  **Project Configuration**:
    -   **Framework Preset**: Vite (Vercel should auto-detect).
    -   **Root Directory**: Click `Edit` and select `frontend`.
    -   **Build Command**: `npm run build` (Default).
    -   **Output Directory**: `dist` (Default).

3.  **Environment Variables**:
    -   Expand the **Environment Variables** section.
    -   Add:
        -   `VITE_API_URL`: `https://your-backend-url.onrender.com` (No trailing slash)
        -   `VITE_WS_URL`: `wss://your-backend-url.onrender.com` (Note **wss://** for secure WebSocket)

4.  **Deploy**:
    -   Click **Deploy**.
    -   Wait for the build.
    -   **Visit**: Click the generated URL (e.g., `https://spellatlas.vercel.app`) to test.

---

## Part 3: Final Configuration

1.  **Secure Backend**:
    -   Go back to **Render Dashboard** -> **Environment**.
    -   Update `ALLOWED_ORIGINS` to your Vercel URL (e.g., `https://spellatlas.vercel.app`).
    -   This prevents other sites from using your API.

2.  **Verify**:
    -   Open your Vercel app.
    -   Check the Console (F12) for connection errors.
    -   If the map loads and you see "Connected to backend simulator" (or similar), you are live!

## Troubleshooting

-   **CORS Errors**: Check `ALLOWED_ORIGINS` in Render matches your Vercel URL exactly (no trailing slash usually).
-   **WebSocket Errors**: Ensure you used `wss://` in Vercel env vars, not `ws://`. Render provides SSL automatically.
-   **Empty Map**: The backend has no data. You may need to expose an API endpoint to trigger a news fetch, or run the fetcher locally and push the JSON (if un-ignored).
