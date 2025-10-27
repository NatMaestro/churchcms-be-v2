# 🚀 Deploy FaithFlow Backend to Render

## Prerequisites

✅ GitHub account  
✅ Render account (free at render.com)  
✅ Your backend code pushed to GitHub

---

## 📋 Step-by-Step Deployment

### Step 1: Push Code to GitHub

```bash
cd faithflow-backend

# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial backend deployment"

# Create GitHub repo and push
git remote add origin https://github.com/yourusername/faithflow-backend.git
git branch -M main
git push -u origin main
```

---

### Step 2: Create PostgreSQL Database on Render

1. Go to **https://dashboard.render.com**
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `faithflow-db`
   - **Database**: `faithflow`
   - **User**: `faithflow`
   - **Region**: Ohio (or nearest to you)
   - **Plan**: Free (or Starter for production)
4. Click **"Create Database"**
5. **Copy the "Internal Database URL"** - you'll need this!

---

### Step 3: Create Web Service on Render

1. Click **"New +"** → **"Web Service"**
2. **Connect your GitHub repository**
3. Configure:
   - **Name**: `faithflow-backend`
   - **Region**: Ohio (same as database)
   - **Branch**: `main`
   - **Root Directory**: `faithflow-backend` (if monorepo) or leave blank
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```
     pip install -r requirements.txt && python manage.py collectstatic --no-input
     ```
   - **Start Command**:
     ```
     gunicorn config.wsgi:application
     ```
   - **Plan**: Free (or Starter for production)

---

### Step 4: Set Environment Variables

In Render dashboard, go to **Environment** tab and add:

```env
# Django Settings
DJANGO_SETTINGS_MODULE=config.settings
SECRET_KEY=your-super-secret-production-key-generate-a-long-random-string
DEBUG=False

# Database (will be auto-filled if you linked the database)
DATABASE_URL=<paste the Internal Database URL from Step 2>

# Allowed Hosts
ALLOWED_HOSTS=.onrender.com,.faithflows.com,*.faithflows.com

# CORS (update with your frontend domain)
CORS_ALLOWED_ORIGINS=https://faithflows.com,https://www.faithflows.com,https://faithflow-studio.vercel.app

# Frontend URL (update with your deployed frontend)
FRONTEND_URL=https://faithflow-studio.vercel.app

# Email (optional - configure if you have SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis (optional - if you add Redis service)
# REDIS_URL=redis://...
```

---

### Step 5: Run Initial Migrations

After deployment, you need to run migrations:

1. Go to your Render service dashboard
2. Click **"Shell"** tab
3. Run:
   ```bash
   python manage.py migrate_schemas --shared
   python manage.py migrate_schemas
   ```

---

### Step 6: Create Your First Church

In the Render shell:

```bash
python quickstart.py
```

Or use Django shell:

```bash
python manage.py shell

from apps.churches.models import Church, Domain
from django.db import connection

# Create church
church = Church.objects.create(
    schema_name='testchurch',
    name='Test Church',
    subdomain='testchurch',
    email='test@church.com',
    plan='premium',
    is_active=True
)

# Create domain
Domain.objects.create(
    domain='testchurch.faithflows.com',
    tenant=church,
    is_primary=True
)

# Create admin user
connection.set_tenant(church)
from apps.authentication.models import User
User.objects.create_user(
    email='admin@testchurch.com',
    password='your-secure-password',
    name='Admin User',
    church=church,
    role='admin',
    is_active=True
)
```

---

### Step 7: Configure Custom Domain (Optional)

**If using custom domain (e.g., api.faithflows.com):**

1. In Render, go to **Settings** → **Custom Domain**
2. Add: `api.faithflows.com`
3. Add CNAME record in your DNS:
   ```
   api.faithflows.com CNAME faithflow-backend.onrender.com
   ```

**For wildcard subdomains:**

```
*.faithflows.com CNAME faithflow-backend.onrender.com
```

---

## 🔧 Production Configuration

### Update settings.py for Production

The backend will automatically use production settings when `DEBUG=False`.

### Static Files

Whitenoise is configured to serve static files efficiently in production.

### Database

Render's PostgreSQL is production-ready with:

- Automatic backups
- High availability
- SSL connections

---

## 🌐 Accessing Your Deployed API

### After Deployment:

**Render URL** (automatic):

```
https://faithflow-backend.onrender.com
```

**With Custom Domain**:

```
https://api.faithflows.com
```

**Church Subdomains** (after DNS setup):

```
https://testchurch.faithflows.com/api/docs/
https://olamchurch.faithflows.com/api/docs/
```

---

## 🧪 Test Your Deployment

```bash
# Test health check
curl https://faithflow-backend.onrender.com/api/docs/

# Test login (replace with your church subdomain)
curl -X POST https://testchurch.faithflows.com/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@testchurch.com","password":"your-password"}'
```

---

## 🐛 Troubleshooting

### Build Fails

**Check:**

- Python version in render.yaml (3.11)
- All packages in requirements.txt are compatible
- Build command is correct

**Solution:** Check build logs in Render dashboard

---

### Migrations Fail

**Run manually in Render Shell:**

```bash
python manage.py migrate_schemas --shared --no-input
python manage.py migrate_schemas --no-input
```

---

### Database Connection Error

**Check:**

- DATABASE_URL environment variable is set
- Database service is running
- Internal Database URL is used (not External)

---

### Static Files Not Loading

**Run:**

```bash
python manage.py collectstatic --no-input
```

---

## 📊 Deployment Checklist

Before going live:

- [ ] GitHub repo created and code pushed
- [ ] Render PostgreSQL database created
- [ ] Render web service created
- [ ] Environment variables configured
- [ ] SECRET_KEY generated (long random string)
- [ ] DEBUG=False
- [ ] ALLOWED_HOSTS updated
- [ ] Migrations run successfully
- [ ] First church created
- [ ] Admin user created
- [ ] Static files collected
- [ ] Swagger UI accessible
- [ ] Login works
- [ ] API endpoints tested
- [ ] Custom domain configured (optional)
- [ ] DNS records added (optional)
- [ ] SSL certificate active

---

## 💰 Pricing

**Render Free Tier:**

- ✅ PostgreSQL: 90 days free (256MB RAM, 1GB storage)
- ✅ Web Service: Free (512MB RAM, spins down after inactivity)
- ⚠️ Spins down after 15 min inactivity (30 sec cold start)

**Render Paid Plans:**

- **Starter**: $7/month (persistent, no spin down)
- **Standard**: $25/month (more resources)
- **Pro**: $85/month (high availability)

**Recommendation for Production:** Starter plan ($7/month)

---

## 🚀 Quick Deployment

**Using Render Blueprint (Fastest):**

1. Push `render.yaml` to your GitHub repo
2. In Render: New → Blueprint
3. Connect repo
4. Render auto-creates database + web service
5. Add environment variables
6. Deploy!

---

## 📝 Post-Deployment

### Update Frontend

Update your frontend `.env`:

```env
VITE_API_URL=https://faithflow-backend.onrender.com/api/v1
# Or with custom domain:
VITE_API_URL=https://api.faithflows.com/api/v1
```

### Seed Data

Use the Render shell to seed data:

```bash
python seed_one_church.py
```

---

**Ready to deploy!** 🎉

**Next:** Push your code to GitHub, then follow the steps above!
