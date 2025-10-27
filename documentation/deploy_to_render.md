# 🚀 Quick Render Deployment Guide

## ✅ Files Ready for Deployment

All deployment files have been created:

- ✅ `render.yaml` - Render blueprint configuration
- ✅ `build.sh` - Build script
- ✅ `runtime.txt` - Python version
- ✅ `requirements.txt` - Updated with gunicorn & whitenoise
- ✅ `config/settings_production.py` - Production settings
- ✅ `.gitignore` - Git ignore file

---

## 🎯 Deployment Steps

### 1️⃣ Push to GitHub

```bash
# In faithflow-backend directory
git init
git add .
git commit -m "Deploy FaithFlow Backend to Render"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/faithflow-backend.git
git push -u origin main
```

---

### 2️⃣ Deploy on Render

**Option A: Using Blueprint (Recommended - Automatic)**

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect your GitHub repo
4. Render will auto-create:
   - PostgreSQL database
   - Web service
5. Click **"Apply"**
6. Wait for deployment (5-10 minutes)

**Option B: Manual Setup**

1. Create PostgreSQL Database:

   - New → PostgreSQL
   - Name: `faithflow-db`
   - Copy **Internal Database URL**

2. Create Web Service:
   - New → Web Service
   - Connect GitHub repo
   - Build Command: `pip install -r requirements.txt && python manage.py collectstatic --no-input`
   - Start Command: `gunicorn config.wsgi:application`
   - Add environment variables (see below)

---

### 3️⃣ Configure Environment Variables

**In Render Web Service → Environment:**

```
SECRET_KEY=<generate-a-long-random-string>
DEBUG=False
DATABASE_URL=<from-postgresql-service>
ALLOWED_HOSTS=.onrender.com,.faithflows.com,*.faithflows.com
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
DJANGO_SETTINGS_MODULE=config.settings
```

**Generate SECRET_KEY:**

```python
# Run locally:
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

### 4️⃣ Run Migrations (After First Deploy)

**In Render Shell:**

```bash
python manage.py migrate_schemas --shared
python manage.py migrate_schemas
```

---

### 5️⃣ Create First Church

**In Render Shell:**

```bash
python manage.py shell
```

```python
from apps.churches.models import Church, Domain
from apps.authentication.models import User
from django.db import connection

# Create church
church = Church.objects.create(
    schema_name='demo',
    name='Demo Church',
    subdomain='demo',
    email='demo@faithflows.com',
    plan='premium',
    is_active=True
)

# Create domain
Domain.objects.create(
    domain='demo.faithflows.com',
    tenant=church,
    is_primary=True
)

# Also add Render domain
Domain.objects.create(
    domain='demo.faithflow-backend.onrender.com',
    tenant=church,
    is_primary=False
)

# Create admin
connection.set_tenant(church)
User.objects.create_user(
    email='admin@demo.com',
    password='SecurePassword123!',
    name='Admin User',
    church=church,
    role='admin'
)

exit()
```

---

## 🌐 Your Deployed URLs

**Render Default:**

```
https://faithflow-backend.onrender.com/api/docs/
```

**With Custom Domain:**

```
https://api.faithflows.com/api/docs/
https://demo.faithflows.com/api/docs/
```

---

## 🔐 Security Checklist

Before going live:

- [ ] DEBUG=False
- [ ] SECRET_KEY is strong and unique
- [ ] ALLOWED_HOSTS configured correctly
- [ ] CORS_ALLOWED_ORIGINS set to your frontend domain
- [ ] Database backups enabled (Render does this automatically)
- [ ] SSL/HTTPS working (Render provides free SSL)
- [ ] Environment variables secured
- [ ] No sensitive data in code
- [ ] .env file in .gitignore
- [ ] Production dependencies installed

---

## 📊 Post-Deployment

### Monitor Your App

**Render Dashboard shows:**

- Deployment logs
- Service health
- Database metrics
- Error logs

### Test Everything

Visit Swagger UI and test:

- ✅ Login
- ✅ Create member
- ✅ Create event
- ✅ Record payment
- ✅ All major features

---

## 🎯 Next: Connect Frontend

After backend is deployed, update frontend:

```typescript
// frontend/.env.production
VITE_API_URL=https://api.faithflows.com/api/v1

// Or if using Render direct:
VITE_API_URL=https://faithflow-backend.onrender.com/api/v1
```

---

## ⚡ Quick Deploy Commands

```bash
# 1. Commit changes
git add .
git commit -m "Ready for deployment"
git push origin main

# 2. Render auto-deploys from GitHub!
# Wait 5-10 minutes

# 3. Run migrations in Render shell
python manage.py migrate_schemas --shared
python manage.py migrate_schemas

# 4. Create first church
python quickstart.py

# 5. Done! 🎉
```

---

**Your backend is ready to deploy!** Push to GitHub and deploy to Render! 🚀
