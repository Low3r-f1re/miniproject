# 🚀 Quick Deployment Guide

Deploy your Travel Planner app to Render.com in 5 minutes!

## Before You Start

Get your API keys ready:
1. **GEMINI_API_KEY**: https://makersuite.google.com/app/apikey
2. **OPENROUTER_API_KEY**: https://openrouter.ai/keys

## Deployment Steps

### 1️⃣ Push to GitHub

```bash
# Add all files
git add .

# Commit changes
git commit -m "Deploy to Render.com"

# Push to GitHub (replace with your repo URL)
git push origin main
```

### 2️⃣ Deploy on Render.com

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub account (if not connected)
4. Select your repository
5. Click **"Apply"**

Render will automatically:
- ✅ Read `render.yaml` configuration
- ✅ Create web service (Flask app)
- ✅ Create PostgreSQL database
- ✅ Install dependencies
- ✅ Run database migrations
- ✅ Start your app with HTTPS

### 3️⃣ Add API Keys

After deployment starts:

1. Go to **your web service** in Render dashboard
2. Click **"Environment"** tab
3. Add these variables:
   - `GEMINI_API_KEY` = your-gemini-key-here
   - `OPENROUTER_API_KEY` = your-openrouter-key-here
4. Click **"Save Changes"**
5. Your app will automatically redeploy

### 4️⃣ Access Your App

Your app will be live at:
```
https://travel-planner-XXXXX.onrender.com
```

(Find the URL in your Render dashboard)

## ⚠️ Important Notes

- **First load is slow** - Free tier sleeps after 15 min inactivity
- **Database is free for 90 days** - Then $7/month or migrate to free alternative
- **Auto-deploy enabled** - Every git push triggers redeploy
- **HTTPS automatic** - SSL certificate included

## 🎯 What's Next?

1. Test your app (signup, login, create trip plans)
2. Share your URL with friends
3. Add custom domain (optional)
4. Set up email notifications (optional)

## 🆘 Having Issues?

**Build failed?**
- Check build logs in Render dashboard
- Verify all files are committed

**App won't start?**
- Make sure API keys are added
- Check logs for errors

**Database error?**
- Wait 2-3 minutes for database to initialize
- Check database service is running

📖 **Need more help?** See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed guide.

---

**That's it! Your app is now public! 🎉**
