# 💰 Commission Tracker Bot

A financial-grade Telegram bot for tracking KES-based commissions, automatically splitting them between two parties, and providing detailed statistics with scheduled summaries.

## ✨ Features

### Core Functionality

- **Commission Entry**: Send numbers directly (e.g., `7500`) to add commissions
- **Automatic 50/50 Split**: Commissions are automatically split between user and partner
- **Solo Override**: Use `solo` keyword for full personal commission
- **Notes Support**: Add optional notes to entries (e.g., `7500 client A`)
- **Month Totals**: See running month totals in commission confirmation messages

### Monthly Lifecycle

- **Weekday Summaries**: Automatic summaries every Friday at 18:00
- **Month-End Summary**: Official statement sent on last day at 23:00
- **New Month Start**: Automatic month transition on 1st at 00:00
- **Immutable Statements**: Each closed month gets a unique statement ID
- **Read-Only Closed Months**: Previous months become locked after closing

### Statistics & Reporting

- **Monthly Stats**: Total, split, entries count, daily/weekly totals, largest/smallest entries, active/inactive days
- **Yearly Stats**: Month-by-month breakdown, averages, largest/smallest months, top weeks
- **CSV Export**: Export commission data for any month or year

### Safety Features

- **Undo Functionality**: Undo last entry within 5 minutes
- **Duplicate Detection**: Alerts for duplicate entries within 2 minutes
- **Extreme Amount Alerts**: Warns if entry is >2x monthly average
- **Month Rollover Confirmation**: Asks for confirmation near month boundaries
- **Zero Activity Alerts**: Notifies if no entries for 7 consecutive days

### Authorization & Access Control

- **Owner-Only Access**: Bot can be restricted to owner and approved users only
- **Authorization Requests**: New users can request access via `/start`
- **Owner Approval**: Owner receives notifications with inline buttons to approve/deny requests
- **User Management**: Owner can approve or revoke user access via commands

### User Interface

- **Menu Buttons**: All commands accessible via Telegram menu button (☰)
- **Inline Keyboards**: Quick action buttons for common commands
- **Command Shortcuts**: Easy access to dashboard, balance, stats, export, and settings

### Automated Reminders

- **Expected Payout Reminder**: Sent on 28th of each month at 18:00
- **Weekly Summary**: Every Friday at 18:00
- **Month-End Statement**: Last day at 23:00

## 📋 Commands

### User Commands

| Command | Description |
| :------ | :---------- |
| `<number>` | Add commission (e.g., `7500` or `7500 client A`) |
| `<number> solo` | Add full personal commission (no split) |
| `/start` | Start the bot and see welcome message |
| `/dashboard` | Show current month dashboard |
| `/balance` | Show owed amounts to partner |
| `/paid <amount>` | Record payout to partner |
| `/undo` | Undo last entry (5 min window) |
| `/stats month [month]` | Show detailed monthly stats |
| `/stats year [year]` | Show detailed yearly stats |
| `/yearly [year]` | Yearly summary |
| `/export [month/year]` | Export CSV summary |
| `/settings` | View bot settings |

### Owner-Only Commands

| Command | Description |
| :------ | :---------- |
| `/approve [user_id]` | Approve user access (or list pending requests) |
| `/revoke <user_id>` | Revoke user access |
| `/clear_db` | Clear all database data (requires confirmation) |

## 🔒 Security Note

**Before pushing to GitHub:**
- Never commit `config.py` (it contains your bot token and user ID)
- Never commit `commissions.db` (it contains user data)
- Use `config.example.py` as a template
- The `.gitignore` file is configured to exclude sensitive files

## 🚀 Setup

### Prerequisites

- Python 3.11+
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))
- Your Telegram User ID (get it from [@userinfobot](https://t.me/userinfobot))

### Installation

1. **Clone or download this repository**

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**:

   Copy the example config file and edit it:

   ```bash
   # Windows (PowerShell)
   Copy-Item config.example.py config.py
   
   # Linux/Mac
   cp config.example.py config.py
   ```

   Then edit `config.py` and set:
   - `BOT_TOKEN`: Your Telegram bot token (from [@BotFather](https://t.me/botfather))
   - `OWNER_USER_ID`: Your Telegram user ID (from [@userinfobot](https://t.me/userinfobot))

   **Alternative**: Set environment variables instead:

   ```bash
   # Windows (PowerShell)
   $env:BOT_TOKEN="your_bot_token_here"
   $env:OWNER_USER_ID="your_telegram_user_id"
   
   # Linux/Mac
   export BOT_TOKEN="your_bot_token_here"
   export OWNER_USER_ID="your_telegram_user_id"
   ```

   Optional environment variables:

   - `DATABASE_PATH`: Path to SQLite database (default: `commissions.db`)
   - `TIMEZONE`: Timezone for scheduling (default: `Africa/Nairobi`)

   ⚠️ **Important**: Never commit `config.py` to version control! It contains sensitive data.

4. **Run the bot**:

   ```bash
   python bot.py
   ```

## 📁 Project Structure

```
tg bot/
├── bot.py              # Main bot application
├── database.py         # Database models and operations
├── utils.py            # Utility functions
├── stats.py            # Statistics calculations
├── config.example.py   # Configuration template (copy to config.py)
├── config.py           # Configuration settings (create from example, NOT in git)
├── requirements.txt    # Python dependencies
├── start.sh            # Startup script for deployment platforms
├── .python-version     # Python version specification
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── commissions.db      # SQLite database (created automatically, NOT in git)
```

## 🗄️ Database Schema

The bot uses SQLite with the following tables:

- **users**: User information and timezone
- **commissions**: Commission entries with splits
- **payouts**: Payout records to partner
- **monthly_summaries**: Closed month statements
- **audit_logs**: Audit trail for all actions
- **authorized_users**: List of authorized users (for access control)
- **pending_authorizations**: Pending authorization requests

## 🚀 Deployment

### Cloud Hosting (24/7)

The bot is ready for deployment on cloud platforms. Recommended platforms:

- **Koyeb** (Free tier available) - ✅ Tested and working
- **Railway** ($5 free credit/month)
- **Render** (Free tier, sleeps after inactivity)
- **Fly.io** (Free tier available)

#### Deployment Steps

1. **Push to GitHub** (already done if you followed setup)

2. **Deploy on your chosen platform**:
   - Connect your GitHub repository
   - Set environment variables:
     - `BOT_TOKEN` - Your Telegram bot token
     - `OWNER_USER_ID` - Your Telegram user ID
     - `DATABASE_PATH` - Optional (default: `commissions.db`)
     - `TIMEZONE` - Optional (default: `Africa/Nairobi`)

3. **Configure build settings**:
   - **Build command**: Leave empty (buildpack handles it)
   - **Run command**: `bash start.sh` or `cd /workspace && python bot.py`
   - **Python version**: 3.11 (specified in `.python-version`)

4. **Important Notes**:
   - The `start.sh` script creates `config.py` from environment variables at runtime
   - Only one bot instance should run at a time (stop local instance when deploying)
   - Database persistence: SQLite files may not persist on some platforms (consider using volumes or external databases)

#### Koyeb Specific

- Use Buildpack (auto-detects Python)
- Run command: `bash start.sh`
- Environment variables are set in the Variables section
- The startup script handles `config.py` creation automatically

## ⚙️ Configuration

Edit `config.py` to customize:

- **Scheduler Times**: Weekly, monthly, and reminder times
- **Safety Settings**: Undo window, duplicate detection, zero activity threshold
- **Split Settings**: Default split ratios (currently 50/50)
- **Authorization**: Owner user ID for access control

## 🔒 Safety & Audit

- All actions are logged in `audit_logs` table
- Closed months are immutable (read-only)
- Duplicate and extreme amount detection
- Timezone-safe operations
- Month rollover handling even if bot was offline
- Owner-only commands for sensitive operations
- Database clear requires explicit confirmation

## 🔐 Authorization System

The bot supports owner-based access control:

1. **Owner Setup**: Set `OWNER_USER_ID` in `config.py` or environment variable
2. **New User Flow**: When unauthorized users send `/start`, they:
   - See an "Authorization Required" message
   - Their request is sent to the owner with inline Approve/Deny buttons
   - Owner can approve or deny via buttons or `/approve`/`/revoke` commands
3. **Owner Commands**: Only the owner can:
   - Approve/revoke user access
   - Clear the database
   - View pending authorization requests

## 📊 Example Usage

```
You: 7500
Bot: ✅ Commission added!
     💰 Amount: KES 7,500.00
     👤 Your Share: KES 3,750.00
     🤝 Partner Share: KES 3,750.00
     📅 Month: 2024-01
     📊 Month Total: KES 7,500.00

You: /dashboard
Bot: 📊 Dashboard - 2024-01
     💰 Total Commission: KES 15,000.00
     👤 Your Share: KES 7,500.00
     🤝 Partner Share: KES 7,500.00
     📝 Entries: 2

You: /stats month
Bot: 📊 Monthly Statistics
     [Detailed stats...]

You: /paid 5000
Bot: ✅ Payout recorded!
     💰 Amount: KES 5,000.00
```

## 🛠️ Development

### Running in Development

The bot includes comprehensive logging. Check console output for:

- Commission entries
- Scheduled task execution
- Error messages
- Authorization requests

### Database Management

**Backup database**:

```bash
cp commissions.db commissions_backup.db
```

**Clear database** (owner only):

Use `/clear_db` command in Telegram (requires confirmation).

**Reset database**:

Delete `commissions.db` file - the bot will recreate it with fresh empty tables on restart.

⚠️ **Warning**: Deleting or clearing the database will permanently delete all data!

## 📝 Notes

- Commissions are stored in KES (Kenyan Shillings)
- Default timezone is Africa/Nairobi (configurable)
- Month format: YYYY-MM (e.g., 2024-01)
- Statement IDs are immutable and unique per month
- CSV exports include all commission details
- Menu buttons (☰) provide quick access to all commands
- Owner is automatically authorized on first use

## 🐛 Troubleshooting

**Bot not responding?**

- Check that `BOT_TOKEN` is set correctly
- Verify internet connection
- Check bot logs for errors

**Scheduled tasks not running?**

- Verify timezone setting in `config.py`
- Check APScheduler logs
- Ensure bot is running continuously

**Database errors?**

- Delete `commissions.db` to reset (⚠️ loses all data)
- Check file permissions
- Verify SQLite is working

**Authorization issues?**

- Verify `OWNER_USER_ID` is set correctly in `config.py` or environment variables
- Check that you're using the correct Telegram user ID
- Ensure the bot is running when authorization requests are sent

**Deployment issues?**

- **ModuleNotFoundError**: Make sure `start.sh` is used as the run command, or set PYTHONPATH correctly
- **Invalid Token**: Verify `BOT_TOKEN` environment variable is set correctly with the complete token
- **Conflict Error**: Only one bot instance can run at a time. Stop local instance when deploying to cloud
- **Config not found**: The `start.sh` script creates `config.py` from environment variables automatically

## 📄 License

This project is provided as-is for commission tracking purposes.

## 🤝 Support

For issues or questions, check the code comments or review the database schema in `database.py`.

---

**Built with**: Python, python-telegram-bot, APScheduler, SQLite
