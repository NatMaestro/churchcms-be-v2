# 🆓 Deploy FaithFlow Backend - Render Free Tier

## ✅ Free Tier Setup (No Shell Access Needed!)

Since Render's free tier doesn't include Shell access, I've created an **automatic setup system** for you!

---

## 🚀 Step-by-Step Deployment

### Step 1: Push to GitHub

```bash
cd faithflow-backend

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Deploy to Render - Free Tier"

# Create GitHub repo at github.com, then:
git remote add origin https://github.com/YOUR_USERNAME/faithflow-backend.git
git branch -M main
git push -u origin main
```

---

### Step 2: Deploy on Render

1. **Go to:** https://dashboard.render.com (sign up/login)

2. **Click:** "New +" → "Blueprint"

3. **Connect your GitHub repository**

4. **Render will detect `render.yaml`** and show:
   - PostgreSQL Database (free tier)
   - Web Service (free tier)

5. **Click "Apply"**

6. **Wait 10-15 minutes** for:
   - Database creation
   - Dependencies installation  
   - **Migrations run automatically!** ✅
   - Service deployment

---

### Step 3: Create Your First Church

The old `POST /api/v1/setup/initial/` endpoint has been removed. Create churches
either through self-service sign-up on the frontend (`/onboarding`) or as a
platform admin (`POST /api/v1/platform/churches/`).

---

### Step 4: (removed)

---

### Step 5: Test Your Deployment

After setup completes, test your church:

```bash
# Login
curl -X POST https://mychurch.faithflow-backend.onrender.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@mychurch.com",
    "password": "YourSecurePassword123!"
  }'
```

**Or visit Swagger:**
```
https://mychurch.faithflow-backend.onrender.com/api/docs/
```

---

## 🌐 Your Deployed URLs

**Replace `mychurch` with your actual subdomain:**

```
Backend API:
https://faithflow-backend.onrender.com/api/docs/

Your Church API:
https://mychurch.faithflow-backend.onrender.com/api/docs/
https://mychurch.faithflow-backend.onrender.com/api/v1/members/
https://mychurch.faithflow-backend.onrender.com/api/v1/events/
https://mychurch.faithflow-backend.onrender.com/api/v1/payments/
```

---

## 🔐 Security Features

✅ **Migrations run automatically** during build  
✅ **Setup endpoint protected** by setup token  
✅ **One-time use** - can only create first church if none exist  
✅ **SSL/HTTPS** automatic (Render provides free SSL)  
✅ **Environment variables** encrypted  

---

## 🎯 Adding More Churches

### Option 1: Via API (Recommended)

Create a super admin endpoint to add new churches via API

### Option 2: Via Database Dashboard

Use Render's database dashboard to manually insert church records

### Option 3: Upgrade to Paid Plan

Get Shell access for $7/month and use:
```bash
python quickstart.py
```

---

## ⚠️ Free Tier Limitations

**Be aware:**
- ⏰ **Spins down after 15 min** of inactivity
- ⏱️ **30 second cold start** when waking up
- 💾 **Limited database** (1GB storage)
- 🚫 **No Shell access** (we worked around this!)
- 📊 **750 hours/month** (enough for 1 service)

**For production:** Upgrade to Starter ($7/month) for:
- ✅ No spin down
- ✅ Shell access
- ✅ Better performance
- ✅ More storage

---

## 🐛 Troubleshooting

### Build Fails

**Check build logs in Render dashboard**

Common issues:
- Python version mismatch
- Missing dependencies
- Database not connected

**Solution:** Check the logs, fix, and push again

---

## 📊 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Render Blueprint deployed
- [ ] Database created (automatic)
- [ ] Web service deployed (automatic)
- [ ] Migrations ran (automatic during build)
- [ ] First church created via sign-up or the platform admin
- [ ] Login tested
- [ ] Swagger UI accessible
- [ ] API endpoints tested

---

## 🎉 Success!

After completing setup, you'll have:

✅ **Backend deployed** on Render  
✅ **Database** with all tables  
✅ **First church** created  
✅ **Admin user** ready  
✅ **API** accessible worldwide  
✅ **Swagger docs** available  

---

## 🔗 Next Steps

1. **Deploy** following steps above
2. **Test** via Swagger UI
3. **Connect your frontend** to the deployed backend
4. **Update DNS** for custom domains (optional)
5. **Go live!** 🎊

---

**Estimated Time:** 20-30 minutes total  
**Cost:** $0 (Free tier)  
**Difficulty:** Easy (mostly waiting for builds)

---

**Ready to deploy!** Start with Step 1: Push to GitHub! 🚀




