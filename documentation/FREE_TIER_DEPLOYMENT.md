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

### Step 3: Get Your SETUP_TOKEN

After deployment completes:

1. Go to your **Web Service** in Render dashboard

2. Click **"Environment"** tab

3. Find **`SETUP_TOKEN`** - click "Show" to reveal it

4. **Copy this token** - you'll need it in the next step!

---

### Step 4: Create Your First Church (Via API!)

Since you don't have Shell access, use this API endpoint:

**Using Postman, Insomnia, or cURL:**

```bash
curl -X POST https://faithflow-backend.onrender.com/api/v1/setup/initial/ \
  -H "Content-Type: application/json" \
  -d '{
    "church_name": "My Church",
    "subdomain": "mychurch",
    "email": "info@mychurch.com",
    "denomination": "Pentecostal",
    "admin_name": "Admin User",
    "admin_email": "admin@mychurch.com",
    "admin_password": "YourSecurePassword123!",
    "setup_token": "paste-your-SETUP_TOKEN-here"
  }'
```

**Or use the Swagger UI:**

1. Go to: `https://faithflow-backend.onrender.com/api/docs/`

2. Find: `POST /api/v1/setup/initial/`

3. Click "Try it out"

4. Fill in the JSON body with your church details

5. **Important:** Use the `SETUP_TOKEN` from Render environment variables!

6. Click "Execute"

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

### Setup Endpoint Returns 403

**Error:** "Invalid setup token"

**Solution:** Make sure you copied the `SETUP_TOKEN` correctly from Render environment variables

---

### Setup Endpoint Returns 400

**Error:** "Setup already completed"

**This is good!** It means a church already exists. The endpoint only works once for security.

---

## 📊 Deployment Checklist

- [ ] Code pushed to GitHub
- [ ] Render Blueprint deployed
- [ ] Database created (automatic)
- [ ] Web service deployed (automatic)
- [ ] Migrations ran (automatic during build)
- [ ] SETUP_TOKEN copied from Render
- [ ] First church created via setup endpoint
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




