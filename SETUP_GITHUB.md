# 🚀 Setting Up for GitHub

## ✅ What I've Done

1. **Created `.gitignore`** - Excludes sensitive files:
   - `config.py` (contains your bot token and user ID)
   - `commissions.db` (contains user data)
   - `__pycache__/`, `venv/`, and other common files

2. **Created `config.example.py`** - Template file with placeholder values

3. **Updated `config.py`** - Removed hardcoded sensitive values (now requires environment variables or manual editing)

4. **Updated README.md** - Added security notes and updated setup instructions

## ⚠️ Important: Restore Your Config

Your `config.py` file has been updated to remove hardcoded values. You need to restore your actual values:

1. **Option 1: Edit config.py directly**
   - Open `config.py`
   - Set `BOT_TOKEN = "your_actual_token_here"`
   - Set `OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "your_user_id_here"))`

2. **Option 2: Use environment variables**
   ```bash
   # Windows (PowerShell)
   $env:BOT_TOKEN="your_actual_token_here"
   $env:OWNER_USER_ID="your_user_id_here"
   
   # Linux/Mac
   export BOT_TOKEN="your_actual_token_here"
   export OWNER_USER_ID="your_user_id_here"
   ```

## 📤 Ready to Push to GitHub

Now you can safely push to GitHub:

```bash
# Initialize git (if not already done)
git init

# Add all files (config.py and commissions.db will be ignored)
git add .

# Commit
git commit -m "Initial commit: Commission Tracker Bot"

# Add your GitHub repository
git remote add origin https://github.com/yourusername/your-repo.git

# Push
git push -u origin main
```

## 🔍 Verify Before Pushing

Double-check that sensitive files are NOT being tracked:

```bash
# Check what will be committed
git status

# Verify config.py is ignored
git check-ignore config.py
# Should output: config.py

# Verify commissions.db is ignored
git check-ignore commissions.db
# Should output: commissions.db
```

## ✅ What Gets Committed

- ✅ All Python source files (`bot.py`, `database.py`, `utils.py`, `stats.py`)
- ✅ `config.example.py` (template, safe to commit)
- ✅ `requirements.txt`
- ✅ `README.md`
- ✅ `.gitignore`

## ❌ What Does NOT Get Committed

- ❌ `config.py` (your actual config with secrets)
- ❌ `commissions.db` (database with user data)
- ❌ `__pycache__/` (Python cache)
- ❌ `venv/` (virtual environment)

## 🔐 Security Reminders

1. **Never commit `config.py`** - It contains your bot token
2. **Never commit `commissions.db`** - It contains user data
3. **If you accidentally committed secrets**, revoke your bot token immediately:
   - Go to [@BotFather](https://t.me/botfather)
   - Use `/revoke` to generate a new token
   - Update your `config.py` with the new token

## 📝 For Contributors

When someone clones your repository, they should:

1. Copy `config.example.py` to `config.py`
2. Fill in their own `BOT_TOKEN` and `OWNER_USER_ID`
3. Run the bot

This way, everyone uses their own configuration without exposing secrets.

