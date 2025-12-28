"""
Main Telegram Bot for Commission Tracker
"""

import logging
from decimal import Decimal
from datetime import datetime
import pytz
import asyncio
from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    MenuButtonCommands,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from database import Database
from utils import (
    get_current_month_year,
    parse_amount,
    is_near_month_rollover,
    format_kes,
    is_duplicate,
    is_extreme_amount,
    parse_month_year,
)
from stats import (
    calculate_monthly_stats,
    calculate_yearly_stats,
    format_monthly_stats,
    format_yearly_stats,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global database instance
db = Database()

# Store last commission for undo
last_commissions = {}  # {user_id: {commission_id, timestamp}}


def check_authorization(user_id: int) -> bool:
    """Check if user is authorized"""
    # Owner is always authorized
    if config.OWNER_USER_ID and user_id == config.OWNER_USER_ID:
        # Auto-authorize owner on first use
        if not db.is_authorized(user_id):
            db.approve_user(user_id, user_id)
        return True
    return db.is_authorized(user_id)


async def require_authorization(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Check authorization and send message if not authorized"""
    if not update.effective_user:
        return False

    user_id = update.effective_user.id

    if check_authorization(user_id):
        return True

    # Not authorized - send message
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if message and hasattr(message, "reply_text"):
        await message.reply_text(  # type: ignore
            "🔒 **Access Denied**\n\n"
            "You are not authorized to use this bot.\n"
            "An authorization request has been sent to the bot owner.\n"
            "Please wait for approval.",
            parse_mode="Markdown",
        )

    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    if not update.effective_user or not update.message:
        return

    user = update.effective_user
    user_id = user.id
    db.get_or_create_user(user_id, user.full_name)

    # Check if user is authorized
    if not check_authorization(user_id):
        # Not authorized - create pending request and notify owner
        db.add_pending_authorization(
            user_id, user.username or None, user.full_name or None
        )

        # Notify owner
        if config.OWNER_USER_ID:
            try:
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "✅ Approve", callback_data=f"auth_approve_{user_id}"
                        ),
                        InlineKeyboardButton(
                            "❌ Deny", callback_data=f"auth_deny_{user_id}"
                        ),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                owner_message = "🔔 **New Authorization Request**\n\n"
                owner_message += f"👤 User: {user.full_name or 'Unknown'}\n"
                owner_message += f"🆔 ID: `{user_id}`\n"
                if user.username:
                    owner_message += f"📱 Username: @{user.username}\n"
                owner_message += (
                    f"\n⏰ Requested: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                owner_message += "\nChoose an action:"

                await context.bot.send_message(
                    chat_id=config.OWNER_USER_ID,
                    text=owner_message,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Failed to notify owner: {e}")

        await update.message.reply_text(
            "🔒 **Authorization Required**\n\n"
            "You are not authorized to use this bot.\n"
            "An authorization request has been sent to the bot owner.\n"
            "Please wait for approval.\n\n"
            "You will be notified once your request is approved.",
            parse_mode="Markdown",
        )
        return

    # User is authorized - show welcome
    # Create inline keyboard for quick actions
    keyboard = [
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="dashboard"),
            InlineKeyboardButton("💰 Balance", callback_data="balance"),
        ],
        [
            InlineKeyboardButton("📈 Stats Month", callback_data="stats_month"),
            InlineKeyboardButton("📅 Stats Year", callback_data="stats_year"),
        ],
        [
            InlineKeyboardButton("📤 Export CSV", callback_data="export"),
            InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome to Commission Tracker Bot, {user.first_name}!\n\n"
        "📝 **How to use:**\n"
        "• Send a number (e.g., `7500`) to add commission\n"
        "• Add a note: `7500 client A`\n"
        "• Use `solo` for full personal commission\n\n"
        "💡 **Quick Actions:** Use the buttons below or the menu button (☰) for commands!\n\n"
        "💡 Just send a number to get started!",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def handle_commission_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle commission entry (number-only messages)"""
    if not update.effective_user or not update.message or not update.message.text:
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id
    text = update.message.text.strip()

    # Parse amount and note
    parts = text.split(maxsplit=1)
    amount_str = parts[0]
    note = parts[1] if len(parts) > 1 else None

    # Check for "solo" override
    is_solo = note and note.lower() == "solo"
    if is_solo:
        note = None

    amount = parse_amount(amount_str)
    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ Invalid amount. Please send a positive number."
        )
        return

    # Get or create user
    user_name = (
        update.effective_user.full_name
        if update.effective_user and update.effective_user.full_name
        else f"User_{user_id}"
    )
    db.get_or_create_user(user_id, user_name)

    # Check for duplicates
    recent_commissions = db.get_commissions(user_id)[:5]  # Last 5
    if is_duplicate(amount, recent_commissions, config.DUPLICATE_DETECTION_MINUTES):
        await update.message.reply_text(
            f"⚠️ Duplicate detected! Same amount ({format_kes(amount)}) was added recently.\n"
            "If this is correct, please confirm by sending the amount again."
        )
        return

    # Check for extreme amounts
    if recent_commissions:
        monthly_commissions = db.get_commissions(user_id)
        if monthly_commissions:
            monthly_total = sum(Decimal(c["amount"]) for c in monthly_commissions)
            monthly_avg = (
                monthly_total / Decimal(str(len(monthly_commissions)))
                if monthly_commissions
                else Decimal("0")
            )
            if is_extreme_amount(amount, monthly_avg, config.EXTREME_AMOUNT_MULTIPLIER):
                ratio = float(amount / monthly_avg) if monthly_avg > 0 else 0.0
                await update.message.reply_text(
                    f"⚠️ Large amount detected: {format_kes(amount)}\n"
                    f"This is {ratio:.1f}x the monthly average.\n"
                    "Please confirm this is correct."
                )

    # Handle month rollover confirmation
    month, year = get_current_month_year(user_id)
    if is_near_month_rollover(user_id):
        # Ask for confirmation
        await update.message.reply_text(
            f"⚠️ Near month rollover detected!\n"
            f"Amount: {format_kes(amount)}\n"
            f"Assign to: **{month}**?\n"
            "Reply 'yes' to confirm or 'no' to cancel."
        )
        # Store pending commission
        if context.user_data is None:
            context.user_data = {}
        context.user_data["pending_commission"] = {
            "amount": amount,
            "note": note,
            "is_solo": is_solo,
            "month": month,
            "year": year,
        }
        return

    # Add commission
    if is_solo:
        split_user = Decimal(str(amount))
        split_partner = Decimal("0")
    else:
        split_user = Decimal(str(amount)) * Decimal(str(config.DEFAULT_SPLIT_USER))
        split_partner = Decimal(str(amount)) * Decimal(
            str(config.DEFAULT_SPLIT_PARTNER)
        )

    commission_id = db.add_commission(
        user_id=user_id,
        amount=amount,
        note=note or "",
        month=month,
        year=year,
        split_user=split_user,
        split_partner=split_partner,
    )

    # Store for undo
    last_commissions[user_id] = {
        "commission_id": commission_id,
        "timestamp": datetime.now(),
    }

    # Get month total after adding this commission
    month_commissions = db.get_commissions(user_id, month, year)
    month_total = sum(Decimal(c["amount"]) for c in month_commissions)
    month_split_user = sum(Decimal(c["split_user"]) for c in month_commissions)
    month_split_partner = sum(Decimal(c["split_partner"]) for c in month_commissions)

    # Send confirmation
    response = "✅ Commission added!\n\n"
    response += f"💰 Amount: {format_kes(amount)}\n"
    response += f"👤 Your Share: {format_kes(split_user)}\n"
    response += f"🤝 Partner Share: {format_kes(split_partner)}\n"
    if note:
        response += f"📝 Note: {note}\n"
    response += f"\n📊 **Month Total ({month}):**\n"
    response += f"💰 Total: {format_kes(month_total)}\n"  # type: ignore
    response += f"👤 Your Total: {format_kes(month_split_user)}\n"  # type: ignore
    response += f"🤝 Partner Total: {format_kes(month_split_partner)}\n"  # type: ignore  # type: ignore
    response += f"\n📅 Month: {month}\n"
    response += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    await update.message.reply_text(response, parse_mode="Markdown")


async def handle_yes_no(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle yes/no responses for month rollover"""
    if not update.effective_user or not update.message or not update.message.text:
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if context.user_data is None or "pending_commission" not in context.user_data:
        return

    if text == "yes":
        pending = context.user_data["pending_commission"]
        amount = pending["amount"]
        note = pending["note"]
        is_solo = pending["is_solo"]
        month = pending["month"]
        year = pending["year"]

        if is_solo:
            split_user = amount
            split_partner = Decimal("0")
        else:
            split_user = amount * Decimal(str(config.DEFAULT_SPLIT_USER))
            split_partner = amount * Decimal(str(config.DEFAULT_SPLIT_PARTNER))

        commission_id = db.add_commission(
            user_id=user_id,
            amount=amount,
            note=note or "",
            month=month,
            year=year,
            split_user=split_user,
            split_partner=split_partner,
        )

        last_commissions[user_id] = {
            "commission_id": commission_id,
            "timestamp": datetime.now(),
        }

        # Get month total after adding this commission
        month_commissions = db.get_commissions(user_id, month, year)
        month_total = sum(Decimal(c["amount"]) for c in month_commissions)
        month_split_user = sum(Decimal(c["split_user"]) for c in month_commissions)
        month_split_partner = sum(
            Decimal(c["split_partner"]) for c in month_commissions
        )

        response = f"✅ Commission added to {month}!\n\n"
        response += f"💰 Amount: {format_kes(amount)}\n"
        response += f"👤 Your Share: {format_kes(split_user)}\n"
        response += f"🤝 Partner Share: {format_kes(split_partner)}\n"
        response += f"\n📊 **Month Total ({month}):**\n"
        response += f"💰 Total: {format_kes(month_total)}\n"  # type: ignore
        response += f"👤 Your Total: {format_kes(month_split_user)}\n"  # type: ignore
        response += f"🤝 Partner Total: {format_kes(month_split_partner)}\n"  # type: ignore
        response += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        await update.message.reply_text(response, parse_mode="Markdown")
        del context.user_data["pending_commission"]
    elif text == "no":
        await update.message.reply_text("❌ Commission entry cancelled.")
        del context.user_data["pending_commission"]


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current month dashboard"""
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not update.effective_user or not message or not hasattr(message, "reply_text"):
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id
    month, year = get_current_month_year(user_id)

    commissions = db.get_commissions(user_id, month, year)
    payouts = db.get_payouts(user_id, month, year)

    stats = calculate_monthly_stats(commissions, payouts)

    response = f"📊 **Dashboard - {month}**\n\n"
    response += f"💰 Total Commission: {format_kes(stats['total_commission'])}\n"
    response += f"👤 Your Share: {format_kes(stats['split_user'])}\n"
    response += f"🤝 Partner Share: {format_kes(stats['split_partner'])}\n"
    response += f"📝 Entries: {stats['entries_count']}\n"

    if payouts:
        response += f"💸 Payouts Made: {format_kes(stats['total_payouts'])}\n"
        response += f"💵 Owed to Partner: {format_kes(stats['owed_to_partner'])}\n"

    if hasattr(message, "reply_text"):
        await message.reply_text(response, parse_mode="Markdown")  # type: ignore


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance/owed amounts"""
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not update.effective_user or not message or not hasattr(message, "reply_text"):
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id
    month, year = get_current_month_year(user_id)

    commissions = db.get_commissions(user_id, month, year)
    payouts = db.get_payouts(user_id, month, year)

    stats = calculate_monthly_stats(commissions, payouts)

    response = "💰 **Balance Summary**\n\n"
    response += f"📅 Current Month: {month}\n\n"
    response += f"🤝 Partner Share: {format_kes(stats['split_partner'])}\n"
    response += f"💸 Payouts Made: {format_kes(stats['total_payouts'])}\n"
    response += f"💵 **Owed to Partner: {format_kes(stats['owed_to_partner'])}**\n"

    if hasattr(message, "reply_text"):
        await message.reply_text(response, parse_mode="Markdown")  # type: ignore


async def paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record payout to partner"""
    if not update.effective_user or not update.message:
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id

    if not context.args or len(context.args) == 0:
        # Show help with list of closed months
        current_month, current_year = get_current_month_year(user_id)
        closed_months = db.get_all_monthly_summaries(user_id)

        response = "❌ Usage: `/paid <amount> [month]`\n\n"
        response += "**Examples:**\n"
        response += "• `/paid 5000` - Record payout for current month\n"
        response += "• `/paid 5000 2025-12` - Record payout for December 2025\n\n"

        if closed_months:
            response += "**Closed Months Available:**\n"
            for summary in closed_months[:5]:  # Show last 5 closed months
                month_key = f"{summary['year']}-{summary['month']}"
                response += f"• {month_key} (Statement: {summary['statement_id']})\n"

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    # Parse amount (first argument)
    amount_str = context.args[0]
    amount = parse_amount(amount_str)

    if amount is None or amount <= 0:
        await update.message.reply_text(
            "❌ Invalid amount. Please provide a positive number."
        )
        return

    # Parse month if provided (second argument), otherwise use current month
    if len(context.args) > 1:
        month_str = " ".join(context.args[1:])
        month, year = parse_month_year(month_str)

        # Check if month is closed
        monthly_summary = db.get_monthly_summary(user_id, month, year)
        if not monthly_summary:
            # Month not closed, check if it's the current month
            current_month, current_year = get_current_month_year(user_id)
            if month != current_month or year != current_year:
                await update.message.reply_text(
                    f"⚠️ Month {month} is not closed yet. You can only record payouts for:\n"
                    f"• Current month ({current_month})\n"
                    f"• Closed months (use `/paid <amount>` for current month)"
                )
                return
    else:
        # Use current month
        month, year = get_current_month_year(user_id)

    # Record the payout
    db.add_payout(user_id, amount, month, year)

    # Get updated stats
    commissions = db.get_commissions(user_id, month, year)
    payouts = db.get_payouts(user_id, month, year)
    stats = calculate_monthly_stats(commissions, payouts)

    monthly_summary = db.get_monthly_summary(user_id, month, year)
    is_closed = monthly_summary is not None

    response = "✅ Payout recorded!\n\n"
    response += f"💰 Amount: {format_kes(amount)}\n"
    response += f"📅 Month: {month}"
    if is_closed:
        response += f" (Closed - {monthly_summary['statement_id']})"
    response += "\n\n"
    response += f"💸 Total Payouts for {month}: {format_kes(stats['total_payouts'])}\n"
    response += f"💵 Remaining Owed: {format_kes(stats['owed_to_partner'])}\n"
    response += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    await update.message.reply_text(response, parse_mode="Markdown")


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Undo last commission entry"""
    if not update.effective_user or not update.message:
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id

    if user_id not in last_commissions:
        await update.message.reply_text("❌ No recent commission to undo.")
        return

    last_comm = last_commissions[user_id]
    time_diff = (datetime.now() - last_comm["timestamp"]).total_seconds() / 60

    if time_diff > config.UNDO_WINDOW_MINUTES:
        await update.message.reply_text(
            f"❌ Undo window expired. Last entry was {int(time_diff)} minutes ago.\n"
            f"Undo is only available within {config.UNDO_WINDOW_MINUTES} minutes."
        )
        del last_commissions[user_id]
        return

    success = db.delete_commission(last_comm["commission_id"], user_id)
    if success:
        await update.message.reply_text("✅ Last commission entry undone!")
        del last_commissions[user_id]
    else:
        await update.message.reply_text("❌ Failed to undo commission entry.")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats command - can be 'stats month' or 'stats year'"""
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not update.effective_user or not message or not hasattr(message, "reply_text"):
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id

    if context.args and len(context.args) > 0 and context.args[0].lower() == "year":
        # Yearly stats
        if len(context.args) > 1:
            try:
                year = int(context.args[1])
            except (ValueError, TypeError, IndexError):
                year = datetime.now().year
        else:
            year = datetime.now().year

        monthly_summaries = db.get_all_monthly_summaries(user_id, year)

        # Get all commissions for the year (even if months aren't closed)
        # First get from closed months
        all_commissions = []
        for summary in monthly_summaries:
            comms = db.get_commissions(user_id, summary["month"], summary["year"])
            all_commissions.extend(comms)

        # Also get commissions for all months of the year (including open months)
        # We need to get all commissions and filter by year
        all_user_commissions = db.get_commissions(user_id)
        year_commissions = [c for c in all_user_commissions if c.get("year") == year]

        # Use year_commissions if we have them, otherwise use all_commissions
        if year_commissions:
            all_commissions = year_commissions

        stats = calculate_yearly_stats(monthly_summaries, all_commissions)
        formatted = format_yearly_stats(stats)
    else:
        # Monthly stats (default)
        if (
            context.args
            and len(context.args) > 0
            and context.args[0].lower() != "month"
        ):
            month_str = context.args[0]
            month, year = parse_month_year(month_str)
        elif (
            context.args
            and len(context.args) > 1
            and context.args[0].lower() == "month"
        ):
            month_str = context.args[1]
            month, year = parse_month_year(month_str)
        else:
            month, year = get_current_month_year(user_id)

        commissions = db.get_commissions(user_id, month, year)
        payouts = db.get_payouts(user_id, month, year)

        stats = calculate_monthly_stats(commissions, payouts)
        formatted = format_monthly_stats(stats)

    if hasattr(message, "reply_text"):
        await message.reply_text(formatted, parse_mode="Markdown")  # type: ignore


async def yearly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yearly summary"""
    if not update.effective_user or not update.message:
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id

    if context.args and len(context.args) > 0:
        try:
            year = int(context.args[0])
        except (ValueError, TypeError):
            year = datetime.now().year
    else:
        year = datetime.now().year

    monthly_summaries = db.get_all_monthly_summaries(user_id, year)
    all_commissions = []
    for summary in monthly_summaries:
        comms = db.get_commissions(user_id, summary["month"], summary["year"])
        all_commissions.extend(comms)

    stats = calculate_yearly_stats(monthly_summaries, all_commissions)
    formatted = format_yearly_stats(stats)

    await update.message.reply_text(formatted, parse_mode="Markdown")


async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export CSV summary"""
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not update.effective_user or not message or not hasattr(message, "reply_text"):
        return

    if not await require_authorization(update, context):
        return

    user_id = update.effective_user.id
    import csv
    import io

    month: str | None = None
    year: int

    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if len(arg) == 4 and arg.isdigit():
            # Year export
            year = int(arg)
            monthly_summaries = db.get_all_monthly_summaries(user_id, year)
            commissions = []
            for summary in monthly_summaries:
                comms = db.get_commissions(user_id, summary["month"], summary["year"])
                commissions.extend(comms)
        else:
            # Month export
            month, year = parse_month_year(arg)
            commissions = db.get_commissions(user_id, month, year)
    else:
        # Current month
        month, year = get_current_month_year(user_id)
        commissions = db.get_commissions(user_id, month, year)

    if not commissions:
        if hasattr(message, "reply_text"):
            await message.reply_text("❌ No data to export.")  # type: ignore
        return

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Amount", "Your Share", "Partner Share", "Note"])

    for comm in commissions:
        writer.writerow(
            [
                comm["date_added"],
                comm["amount"],
                comm["split_user"],
                comm["split_partner"],
                comm["note"] or "",
            ]
        )

    csv_data = output.getvalue()
    output.close()

    # Send as document
    filename = f"commissions_{year}_{month if month else 'year'}.csv"
    if hasattr(message, "reply_document"):
        await message.reply_document(  # type: ignore
            document=io.BytesIO(csv_data.encode("utf-8")), filename=filename
        )


async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings"""
    message = update.message or (
        update.callback_query.message if update.callback_query else None
    )
    if not update.effective_user or not message or not hasattr(message, "reply_text"):
        return

    if not await require_authorization(update, context):
        return

    response = "⚙️ **Settings**\n\n"
    response += f"📅 Timezone: {config.DEFAULT_TIMEZONE}\n"
    response += (
        f"⏰ Weekly Summary: Friday {config.WEEKLY_SUMMARY_TIME.strftime('%H:%M')}\n"
    )
    response += f"⏰ Month-End Summary: Last day {config.MONTH_END_SUMMARY_TIME.strftime('%H:%M')}\n"
    response += (
        f"⏰ Payout Reminder: 28th {config.PAYOUT_REMINDER_TIME.strftime('%H:%M')}\n"
    )
    response += f"↩️ Undo Window: {config.UNDO_WINDOW_MINUTES} minutes\n"
    response += (
        f"🔍 Duplicate Detection: {config.DUPLICATE_DETECTION_MINUTES} minutes\n"
    )
    response += f"⚠️ Zero Activity Alert: {config.ZERO_ACTIVITY_DAYS} days\n"

    await message.reply_text(response, parse_mode="Markdown")  # type: ignore


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses"""
    query = update.callback_query
    if not query or not update.effective_user:
        return

    await query.answer()

    # Handle authorization approve/deny buttons (owner only)
    if query.data and query.data.startswith("auth_"):
        if not config.OWNER_USER_ID or update.effective_user.id != config.OWNER_USER_ID:
            await query.edit_message_text("❌ Only the bot owner can authorize users.")
            return

        if query.data.startswith("auth_approve_"):
            user_id_to_approve = int(query.data.split("_")[2])
            success = db.approve_user(user_id_to_approve, update.effective_user.id)

            if success:
                # Notify the approved user
                try:
                    await context.bot.send_message(
                        chat_id=user_id_to_approve,
                        text="✅ **Authorization Approved!**\n\n"
                        "You can now use the bot. Send /start to begin!",
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    logger.error(f"Failed to notify approved user: {e}")

                await query.edit_message_text(
                    f"✅ User {user_id_to_approve} has been approved and notified."
                )
            else:
                await query.edit_message_text(
                    "❌ User is already authorized or approval failed."
                )

        elif query.data.startswith("auth_deny_"):
            user_id_to_deny = int(query.data.split("_")[2])
            # Remove from pending
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM pending_authorizations WHERE user_id = ?",
                (user_id_to_deny,),
            )
            conn.commit()
            conn.close()

            # Notify the denied user
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_deny,
                    text="❌ **Authorization Denied**\n\n"
                    "Your request to use this bot has been denied.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Failed to notify denied user: {e}")

            await query.edit_message_text(
                f"❌ User {user_id_to_deny} has been denied and notified."
            )

        return

    # Handle clear database confirmation (owner only)
    if query.data and query.data.startswith("clear_db_"):
        if not config.OWNER_USER_ID or update.effective_user.id != config.OWNER_USER_ID:
            await query.edit_message_text(
                "❌ Only the bot owner can clear the database."
            )
            return

        if query.data == "clear_db_confirm":
            try:
                db.clear_database()
                await query.edit_message_text(
                    "✅ **Database Cleared Successfully**\n\n"
                    "All data has been permanently deleted.\n"
                    "The database schema remains intact.",
                    parse_mode="Markdown",
                )
                logger.info(f"Database cleared by user {update.effective_user.id}")
            except Exception as e:
                await query.edit_message_text(
                    f"❌ **Error clearing database:**\n\n{str(e)}"
                )
                logger.error(f"Failed to clear database: {e}")
        elif query.data == "clear_db_cancel":
            await query.edit_message_text("❌ Database clear cancelled.")

        return

    # Regular button callbacks (require authorization)
    if not await require_authorization(update, context):
        return

    if query.data == "dashboard":
        await dashboard(update, context)
    elif query.data == "balance":
        await balance(update, context)
    elif query.data == "stats_month":
        # Temporarily set args for monthly stats
        original_args = context.args
        context.args = ["month"]
        await stats_command(update, context)
        context.args = original_args
    elif query.data == "stats_year":
        # Temporarily set args for yearly stats
        original_args = context.args
        context.args = ["year"]
        await stats_command(update, context)
        context.args = original_args
    elif query.data == "export":
        await export_csv(update, context)
    elif query.data == "settings":
        await settings(update, context)


# Owner Commands
async def approve_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a user (owner only)"""
    if not update.effective_user or not update.message:
        return

    if not config.OWNER_USER_ID or update.effective_user.id != config.OWNER_USER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not context.args or len(context.args) == 0:
        # Show pending requests
        pending = db.get_pending_authorizations()
        if not pending:
            await update.message.reply_text("✅ No pending authorization requests.")
            return

        response = "📋 **Pending Authorization Requests:**\n\n"
        for req in pending:
            response += f"🆔 ID: `{req['user_id']}`\n"
            if req["username"]:
                response += f"📱 Username: @{req['username']}\n"
            if req["full_name"]:
                response += f"👤 Name: {req['full_name']}\n"
            response += f"⏰ Requested: {req['requested_at']}\n"
            response += f"✅ Approve: `/approve {req['user_id']}`\n"
            response += f"❌ Deny: `/revoke {req['user_id']}`\n\n"

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    try:
        user_id_to_approve = int(context.args[0])
        success = db.approve_user(user_id_to_approve, update.effective_user.id)

        if success:
            # Notify the approved user
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_approve,
                    text="✅ **Authorization Approved!**\n\n"
                    "You can now use the bot. Send /start to begin!",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Failed to notify approved user: {e}")

            await update.message.reply_text(
                f"✅ User {user_id_to_approve} has been approved and notified."
            )
        else:
            await update.message.reply_text(
                "❌ User is already authorized or approval failed."
            )
    except (ValueError, TypeError):
        await update.message.reply_text(
            "❌ Invalid user ID. Usage: `/approve <user_id>`", parse_mode="Markdown"
        )


async def revoke_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revoke a user's authorization (owner only)"""
    if not update.effective_user or not update.message:
        return

    if not config.OWNER_USER_ID or update.effective_user.id != config.OWNER_USER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    if not context.args or len(context.args) == 0:
        # Show authorized users
        authorized = db.get_authorized_users()
        if not authorized:
            await update.message.reply_text("✅ No authorized users.")
            return

        response = "👥 **Authorized Users:**\n\n"
        for user in authorized:
            response += f"🆔 ID: `{user['user_id']}`\n"
            if user.get("name"):
                response += f"👤 Name: {user['name']}\n"
            response += f"⏰ Authorized: {user['authorized_at']}\n"
            response += f"❌ Revoke: `/revoke {user['user_id']}`\n\n"

        await update.message.reply_text(response, parse_mode="Markdown")
        return

    try:
        user_id_to_revoke = int(context.args[0])

        # Don't allow revoking owner
        if user_id_to_revoke == config.OWNER_USER_ID:
            await update.message.reply_text("❌ Cannot revoke the bot owner.")
            return

        success = db.revoke_user(user_id_to_revoke)

        if success:
            # Notify the revoked user
            try:
                await context.bot.send_message(
                    chat_id=user_id_to_revoke,
                    text="❌ **Authorization Revoked**\n\n"
                    "Your access to this bot has been revoked.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Failed to notify revoked user: {e}")

            await update.message.reply_text(
                f"❌ User {user_id_to_revoke} has been revoked and notified."
            )
        else:
            await update.message.reply_text(
                "❌ User is not authorized or revocation failed."
            )
    except (ValueError, TypeError):
        await update.message.reply_text(
            "❌ Invalid user ID. Usage: `/revoke <user_id>`", parse_mode="Markdown"
        )


async def clear_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear database (owner only, requires confirmation)"""
    if not update.effective_user or not update.message:
        return

    if not config.OWNER_USER_ID or update.effective_user.id != config.OWNER_USER_ID:
        await update.message.reply_text("❌ Only the bot owner can use this command.")
        return

    # Show confirmation with inline buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm Clear", callback_data="clear_db_confirm"),
            InlineKeyboardButton("❌ Cancel", callback_data="clear_db_cancel"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ **WARNING: Clear Database**\n\n"
        "This will **PERMANENTLY DELETE** all data:\n"
        "• All commissions\n"
        "• All payouts\n"
        "• All monthly summaries\n"
        "• All audit logs\n"
        "• All users and authorizations\n\n"
        "⚠️ **This action cannot be undone!**\n\n"
        "Are you sure you want to proceed?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


# Scheduler Tasks
async def send_weekly_summary(context):
    """Send weekly summary every Friday"""
    app = context.job.data
    users = db.get_all_users()

    # Only send to authorized users
    users = [u for u in users if check_authorization(u["user_id"])]

    for user in users:
        user_id = user["user_id"]
        month, year = get_current_month_year(user_id)
        commissions = db.get_commissions(user_id, month, year)
        payouts = db.get_payouts(user_id, month, year)

        stats = calculate_monthly_stats(commissions, payouts)

        message = f"📊 **Weekly Summary - {month}**\n\n"
        message += f"💰 Month-to-Date: {format_kes(stats['total_commission'])}\n"
        message += f"👤 Your Share: {format_kes(stats['split_user'])}\n"
        message += f"🤝 Partner Share: {format_kes(stats['split_partner'])}\n"
        message += f"📝 Entries This Month: {stats['entries_count']}\n"
        message += f"📅 Active Days: {stats['days_active']}\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            await app.bot.send_message(
                chat_id=user_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send weekly summary to {user_id}: {e}")


async def send_month_end_summary(context):
    """Send month-end summary on last day at 23:00"""
    app = context.job.data
    users = db.get_all_users()

    # Only send to authorized users
    users = [u for u in users if check_authorization(u["user_id"])]

    for user in users:
        user_id = user["user_id"]
        month, year = get_current_month_year(user_id)

        # Close the month
        statement_id = db.close_month(user_id, month, year)

        commissions = db.get_commissions(user_id, month, year)
        payouts = db.get_payouts(user_id, month, year)
        stats = calculate_monthly_stats(commissions, payouts)

        message = f"📋 **Month-End Statement - {month}**\n\n"
        message += f"🆔 Statement ID: `{statement_id}`\n\n"
        message += f"💰 Total Commission: {format_kes(stats['total_commission'])}\n"
        message += f"👤 Your Share: {format_kes(stats['split_user'])}\n"
        message += f"🤝 Partner Share: {format_kes(stats['split_partner'])}\n"
        message += f"📝 Total Entries: {stats['entries_count']}\n"
        if payouts:
            message += f"💸 Payouts Made: {format_kes(stats['total_payouts'])}\n"
            message += f"💵 Owed to Partner: {format_kes(stats['owed_to_partner'])}\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        message += "\n✅ Month closed and locked."

        try:
            await app.bot.send_message(
                chat_id=user_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send month-end summary to {user_id}: {e}")


async def start_new_month(context):
    """Start new month on 1st at 00:00"""
    app = context.job.data
    users = db.get_all_users()

    # Only send to authorized users
    users = [u for u in users if check_authorization(u["user_id"])]

    for user in users:
        user_id = user["user_id"]
        month, year = get_current_month_year(user_id)

        message = "🎉 **New Month Started!**\n\n"
        message += f"📅 Current Month: {month}\n"
        message += "💰 Starting Balance: KES 0.00\n"
        message += "\nReady to track commissions! Just send a number to add an entry.\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            await app.bot.send_message(
                chat_id=user_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send new month notification to {user_id}: {e}")


async def send_payout_reminder(context):
    """Send payout reminder on 28th at 18:00"""
    app = context.job.data
    users = db.get_all_users()

    # Only send to authorized users
    users = [u for u in users if check_authorization(u["user_id"])]

    for user in users:
        user_id = user["user_id"]
        month, year = get_current_month_year(user_id)
        commissions = db.get_commissions(user_id, month, year)
        payouts = db.get_payouts(user_id, month, year)

        stats = calculate_monthly_stats(commissions, payouts)

        message = "💵 **Expected Payout Reminder**\n\n"
        message += f"📅 Month: {month}\n"
        message += f"🤝 Partner Share: {format_kes(stats['split_partner'])}\n"
        if payouts:
            message += f"💸 Payouts Made: {format_kes(stats['total_payouts'])}\n"
            message += f"💵 **Remaining: {format_kes(stats['owed_to_partner'])}**\n"
        else:
            message += f"💵 **Total Owed: {format_kes(stats['owed_to_partner'])}**\n"
        message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        try:
            await app.bot.send_message(
                chat_id=user_id, text=message, parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send payout reminder to {user_id}: {e}")


async def check_zero_activity(context):
    """Check for zero activity and alert"""
    app = context.job.data
    users = db.get_all_users()

    # Only send to authorized users
    users = [u for u in users if check_authorization(u["user_id"])]

    for user in users:
        user_id = user["user_id"]
        commissions = db.get_commissions(user_id)

        if not commissions:
            continue

        # Get last commission date
        from dateutil import parser as date_parser

        last_comm = commissions[0]  # Already sorted by date_added DESC
        try:
            last_date = date_parser.parse(last_comm["date_added"])
            if isinstance(last_date, datetime) and not last_date.tzinfo:
                last_date = pytz.UTC.localize(last_date)

            days_since = (datetime.now(pytz.UTC) - last_date).days

            if days_since >= config.ZERO_ACTIVITY_DAYS:
                message = "⚠️ **Zero Activity Alert**\n\n"
                message += f"No commission entries for {days_since} days.\n"
                message += f"Last entry: {last_date.strftime('%Y-%m-%d')}\n"
                message += "\nIs everything okay?"

                try:
                    await app.bot.send_message(
                        chat_id=user_id, text=message, parse_mode="Markdown"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to send zero activity alert to {user_id}: {e}"
                    )
        except Exception as e:
            logger.error(f"Error checking zero activity for {user_id}: {e}")


def setup_scheduler(app: Application):
    """Setup scheduled tasks"""
    tz = pytz.timezone(config.DEFAULT_TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    # Create a simple context object for scheduler jobs
    class JobContext:
        def __init__(self, application):
            self.job = type("Job", (), {"data": application})()

    job_context = JobContext(app)

    # Weekly summary - Every Friday at 18:00
    scheduler.add_job(
        send_weekly_summary,
        trigger=CronTrigger(day_of_week="fri", hour=18, minute=0, timezone=tz),
        args=[job_context],
    )

    # Month-end summary - Last day at 23:00
    scheduler.add_job(
        send_month_end_summary,
        trigger=CronTrigger(day="last", hour=23, minute=0, timezone=tz),
        args=[job_context],
    )

    # New month start - 1st at 00:00
    scheduler.add_job(
        start_new_month,
        trigger=CronTrigger(day=1, hour=0, minute=0, timezone=tz),
        args=[job_context],
    )

    # Payout reminder - 28th at 18:00
    scheduler.add_job(
        send_payout_reminder,
        trigger=CronTrigger(day=28, hour=18, minute=0, timezone=tz),
        args=[job_context],
    )

    # Zero activity check - Daily at 09:00
    scheduler.add_job(
        check_zero_activity,
        trigger=CronTrigger(hour=9, minute=0, timezone=tz),
        args=[job_context],
    )

    # Don't start here - will be started after event loop is running
    return scheduler


async def post_init(application: Application) -> None:
    """Start scheduler after application is initialized"""
    scheduler = application.bot_data.get("scheduler")
    if scheduler:
        scheduler.start()
        logger.info("Scheduler started")

    # Set up menu buttons after a short delay to ensure bot is fully initialized
    import asyncio

    await asyncio.sleep(2)  # Wait 2 seconds for bot to fully initialize

    try:
        commands = [
            BotCommand("start", "Start the bot and see welcome message"),
            BotCommand("dashboard", "View current month dashboard"),
            BotCommand("balance", "Show balance and owed amounts"),
            BotCommand("paid", "Record payout to partner"),
            BotCommand("undo", "Undo last commission entry"),
            BotCommand("stats", "View statistics (month or year)"),
            BotCommand("yearly", "View yearly summary"),
            BotCommand("export", "Export CSV data"),
            BotCommand("settings", "View bot settings"),
            BotCommand("approve", "Approve user access (owner only)"),
            BotCommand("revoke", "Revoke user access (owner only)"),
            BotCommand("clear_db", "Clear all database data (owner only)"),
        ]
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Menu buttons configured")
    except Exception as e:
        logger.warning(f"Could not set menu buttons: {e}")


async def setup_menu_buttons(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set up menu buttons after bot is fully initialized"""
    application = context.application
    commands = [
        BotCommand("start", "Start the bot and see welcome message"),
        BotCommand("dashboard", "View current month dashboard"),
        BotCommand("balance", "Show balance and owed amounts"),
        BotCommand("paid", "Record payout to partner"),
        BotCommand("undo", "Undo last commission entry"),
        BotCommand("stats", "View statistics (month or year)"),
        BotCommand("yearly", "View yearly summary"),
        BotCommand("export", "Export CSV data"),
        BotCommand("settings", "View bot settings"),
        BotCommand("approve", "Approve user access (owner only)"),
        BotCommand("revoke", "Revoke user access (owner only)"),
        BotCommand("clear_db", "Clear all database data (owner only)"),
    ]

    try:
        await application.bot.set_my_commands(commands)
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        logger.info("Menu buttons configured")
    except Exception as e:
        logger.warning(f"Could not set menu buttons: {e}")


def main():
    """Main function to run the bot"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set! Please set it as an environment variable.")
        return

    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("dashboard", dashboard))
    application.add_handler(CommandHandler("balance", balance))
    application.add_handler(CommandHandler("paid", paid))
    application.add_handler(CommandHandler("undo", undo))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("yearly", yearly))
    application.add_handler(CommandHandler("export", export_csv))
    application.add_handler(CommandHandler("settings", settings))

    # Owner-only commands
    application.add_handler(CommandHandler("approve", approve_user))
    application.add_handler(CommandHandler("revoke", revoke_user))
    application.add_handler(CommandHandler("clear_db", clear_db))

    # Handle commission messages (numbers)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_commission_message)
    )

    # Handle yes/no responses
    application.add_handler(MessageHandler(filters.Regex("^(yes|no)$"), handle_yes_no))

    # Add callback handler for inline buttons
    application.add_handler(CallbackQueryHandler(button_callback))

    # Setup scheduler and store it in bot_data
    scheduler = setup_scheduler(application)
    application.bot_data["scheduler"] = scheduler

    # Add post_init to start scheduler after event loop is running
    application.post_init = post_init

    # Start health check server for cloud platforms
    async def health_check():
        """Simple HTTP health check server for cloud platforms"""
        app = web.Application()
        
        async def health_handler(request):
            return web.Response(text="OK", status=200)
        
        app.router.add_get("/", health_handler)
        app.router.add_get("/health", health_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        logger.info("Health check server started on port 8000")
    
    # Start health check in background
    loop = asyncio.get_event_loop()
    loop.create_task(health_check())

    # Start bot
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
