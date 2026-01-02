# Deployment Guide

## Quick Setup: Persistent Storage on Koyeb

### ✅ Quick Checklist

1. **Create Volume**: Koyeb Dashboard → Volumes → Create volume (1 GB, same region as service)
2. **Attach to Service**: Service → Volumes tab → Attach volume → Mount at `/persistent`
3. **Redeploy**: Service will restart and use persistent storage automatically
4. **Verify**: Database will persist at `/persistent/commissions.db`

**That's it!** The bot is already configured to use persistent storage automatically.

---

## Database Persistence on Koyeb

### ⚠️ Important: Database Storage

By default, Koyeb uses **ephemeral storage**, which means your database will be **lost** when:
- The service restarts
- You redeploy the application
- The container is recreated

### Solutions

#### Option 1: Enable Koyeb Volumes (Recommended for SQLite)

Koyeb offers **Volumes** (technical preview) for persistent block storage. Here's how to set it up:

**Step-by-Step Instructions:**

1. **Create a Volume in Koyeb**:
   - Go to [Koyeb Dashboard](https://app.koyeb.com)
   - Click on **"Volumes"** in the left sidebar
   - Click **"Create volume"**
   - Configure:
     - **Name**: `commission-bot-db` (or any name you prefer)
     - **Size**: 1 GB (minimum, sufficient for SQLite)
     - **Region**: Same region as your service (important!)
   - Click **"Create"**

2. **Attach Volume to Your Service**:
   - Go to your **Service** settings
   - Click on **"Volumes"** tab
   - Click **"Attach volume"**
   - Select the volume you just created
   - Set **Mount path**: `/persistent` (or `/data` - the bot will auto-detect)
   - Click **"Attach"**

3. **Set Environment Variable (Optional)**:
   - In your service settings, go to **"Environment Variables"**
   - Add: `PERSISTENT_STORAGE_PATH=/persistent` (if you used a different mount path)
   - The bot automatically detects `/persistent` by default

4. **Redeploy Your Service**:
   - The service will restart and use the persistent volume
   - Your database will now persist across deployments!

5. **Verify It's Working**:
   - Add some test data to your bot
   - Redeploy or restart the service
   - Check that your data is still there
   - The database file is stored at `/persistent/commissions.db`

**Important Notes**:
- ⚠️ Volumes are in **technical preview** - back up important data
- Volumes are **region-specific** - ensure your service and volume are in the same region
- The bot automatically uses persistent storage if `/persistent` exists
- Database file will be stored at `/persistent/commissions.db`

#### Option 2: Use External Database Service

For production use, consider using an external database:

1. **Free PostgreSQL options**:
   - [Supabase](https://supabase.com) - Free tier available
   - [Neon](https://neon.tech) - Free tier available
   - [Railway](https://railway.app) - $5 free credit/month

2. **Update your deployment**:
   - Install PostgreSQL adapter: Add `psycopg2-binary` to `requirements.txt`
   - Update `database.py` to support PostgreSQL connection strings
   - Set `DATABASE_PATH` environment variable to your PostgreSQL connection string

#### Option 3: Regular Backups (Temporary Solution)

If you can't use persistent storage:

1. **Export your data regularly**:
   - Use the `/export` command to download CSV files
   - Keep backups of your local database file

2. **Restore after redeploy**:
   - Use the export files to recreate entries
   - Or restore from a database backup if you have one

### Current Status

After the recent deployment, your database was reset because:
- The container was recreated with the new code
- Ephemeral storage was cleared
- No persistent volume was configured

### Next Steps

1. **For immediate use**: Start fresh - the bot will work, but you'll need to re-enter data
2. **For production**: Set up persistent storage or external database (see options above)
3. **For testing**: Ephemeral storage is fine - data will reset on each deploy

### Environment Variables for Koyeb

Required:
- `BOT_TOKEN` - Your Telegram bot token
- `OWNER_USER_ID` - Your Telegram user ID

Optional:
- `DATABASE_PATH` - Database file path (default: `commissions.db` or `/persistent/commissions.db` if persistent storage available)
- `PERSISTENT_STORAGE_PATH` - Path to persistent volume (default: `/persistent`)
- `TIMEZONE` - Timezone for scheduling (default: `Africa/Nairobi`)

