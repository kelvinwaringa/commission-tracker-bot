"""
Statistics calculation for Commission Tracker Bot
"""

from decimal import Decimal
from typing import Dict, List, Optional
from utils import format_kes, get_days_active, get_weekly_totals, get_daily_totals


def calculate_monthly_stats(
    commissions: List[Dict], payouts: Optional[List[Dict]] = None
) -> Dict:
    """Calculate detailed monthly statistics"""
    if payouts is None:
        payouts = []
    if not commissions:
        return {
            "total_commission": Decimal("0"),
            "split_user": Decimal("0"),
            "split_partner": Decimal("0"),
            "entries_count": 0,
            "largest_entry": None,
            "smallest_entry": None,
            "daily_totals": {},
            "weekly_totals": {},
            "days_active": 0,
            "days_inactive": 0,
            "average_per_entry": Decimal("0"),
            "total_payouts": Decimal("0"),
            "owed_to_partner": Decimal("0"),
        }

    total_commission = sum(Decimal(c["amount"]) for c in commissions)
    split_user = sum(Decimal(c["split_user"]) for c in commissions)
    split_partner = sum(Decimal(c["split_partner"]) for c in commissions)

    largest = max(commissions, key=lambda x: Decimal(x["amount"]))
    smallest = min(commissions, key=lambda x: Decimal(x["amount"]))

    daily_totals = get_daily_totals(commissions)
    weekly_totals = get_weekly_totals(commissions)
    days_active = get_days_active(commissions)

    # Calculate days inactive (assuming 30-day month for simplicity)
    # In production, use actual days in month
    days_inactive = 30 - days_active

    total_payouts = (
        sum(Decimal(p["amount"]) for p in payouts) if payouts else Decimal("0")
    )
    owed_to_partner = split_partner - total_payouts

    return {
        "total_commission": total_commission,
        "split_user": split_user,
        "split_partner": split_partner,
        "entries_count": len(commissions),
        "largest_entry": largest,
        "smallest_entry": smallest,
        "daily_totals": daily_totals,
        "weekly_totals": weekly_totals,
        "days_active": days_active,
        "days_inactive": days_inactive,
        "average_per_entry": total_commission / len(commissions)
        if commissions
        else Decimal("0"),
        "total_payouts": total_payouts,
        "owed_to_partner": owed_to_partner,
    }


def calculate_yearly_stats(
    monthly_summaries: List[Dict], commissions: Optional[List[Dict]] = None
) -> Dict:
    """Calculate detailed yearly statistics"""
    if commissions is None:
        commissions = []
    if not monthly_summaries:
        return {
            "total_commission": Decimal("0"),
            "total_split_user": Decimal("0"),
            "total_split_partner": Decimal("0"),
            "months_active": 0,
            "monthly_breakdown": {},
            "largest_month": None,
            "smallest_month": None,
            "average_per_month": Decimal("0"),
            "total_entries": 0,
            "top_weeks": [],
        }

    total_commission = sum(Decimal(m["total_commission"]) for m in monthly_summaries)
    total_split_user = sum(Decimal(m["split_user"]) for m in monthly_summaries)
    total_split_partner = sum(Decimal(m["split_partner"]) for m in monthly_summaries)

    monthly_breakdown = {}
    for summary in monthly_summaries:
        month_key = f"{summary['year']}-{summary['month']}"
        monthly_breakdown[month_key] = {
            "total": Decimal(summary["total_commission"]),
            "split_user": Decimal(summary["split_user"]),
            "split_partner": Decimal(summary["split_partner"]),
            "statement_id": summary["statement_id"],
        }

    largest_month = max(monthly_summaries, key=lambda x: Decimal(x["total_commission"]))
    smallest_month = min(
        monthly_summaries, key=lambda x: Decimal(x["total_commission"])
    )

    # Calculate weekly stats if commissions provided
    top_weeks = []
    if commissions:
        weekly_totals = get_weekly_totals(commissions)
        top_weeks = sorted(weekly_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    total_entries = len(commissions) if commissions else 0

    return {
        "total_commission": total_commission,
        "total_split_user": total_split_user,
        "total_split_partner": total_split_partner,
        "months_active": len(monthly_summaries),
        "monthly_breakdown": monthly_breakdown,
        "largest_month": largest_month,
        "smallest_month": smallest_month,
        "average_per_month": total_commission / len(monthly_summaries)
        if monthly_summaries
        else Decimal("0"),
        "total_entries": total_entries,
        "top_weeks": top_weeks,
    }


def format_monthly_stats(stats: Dict) -> str:
    """Format monthly stats as readable text"""
    lines = []
    lines.append("📊 **Monthly Statistics**\n")

    lines.append(f"💰 Total Commission: {format_kes(stats['total_commission'])}")
    lines.append(f"👤 Your Share: {format_kes(stats['split_user'])}")
    lines.append(f"🤝 Partner Share: {format_kes(stats['split_partner'])}")
    lines.append(f"📝 Entries: {stats['entries_count']}")
    lines.append(f"📈 Average per Entry: {format_kes(stats['average_per_entry'])}")

    if stats["largest_entry"]:
        lines.append(
            f"\n🔥 Largest Entry: {format_kes(Decimal(stats['largest_entry']['amount']))}"
        )
        if stats["largest_entry"].get("note"):
            lines.append(f"   Note: {stats['largest_entry']['note']}")

    if stats["smallest_entry"]:
        lines.append(
            f"❄️ Smallest Entry: {format_kes(Decimal(stats['smallest_entry']['amount']))}"
        )
        if stats["smallest_entry"].get("note"):
            lines.append(f"   Note: {stats['smallest_entry']['note']}")

    lines.append("\n📅 Activity:")
    lines.append(f"   Active Days: {stats['days_active']}")
    lines.append(f"   Inactive Days: {stats['days_inactive']}")

    if stats["weekly_totals"]:
        lines.append("\n📊 Weekly Totals:")
        for week, total in sorted(stats["weekly_totals"].items()):
            lines.append(f"   {week}: {format_kes(total)}")

    if stats["total_payouts"] > 0:
        lines.append(f"\n💸 Payouts Made: {format_kes(stats['total_payouts'])}")
        lines.append(f"💵 Owed to Partner: {format_kes(stats['owed_to_partner'])}")

    return "\n".join(lines)


def format_yearly_stats(stats: Dict) -> str:
    """Format yearly stats as readable text"""
    lines = []
    lines.append("📊 **Yearly Statistics**\n")

    lines.append(f"💰 Total Commission: {format_kes(stats['total_commission'])}")
    lines.append(f"👤 Your Total Share: {format_kes(stats['total_split_user'])}")
    lines.append(f"🤝 Partner Total Share: {format_kes(stats['total_split_partner'])}")
    lines.append(f"📅 Active Months: {stats['months_active']}")
    lines.append(f"📈 Average per Month: {format_kes(stats['average_per_month'])}")
    lines.append(f"📝 Total Entries: {stats['total_entries']}")

    if stats["largest_month"]:
        month_key = (
            f"{stats['largest_month']['year']}-{stats['largest_month']['month']}"
        )
        lines.append(f"\n🔥 Largest Month: {month_key}")
        lines.append(
            f"   Total: {format_kes(Decimal(stats['largest_month']['total_commission']))}"
        )
        lines.append(f"   Statement: {stats['largest_month']['statement_id']}")

    if stats["smallest_month"]:
        month_key = (
            f"{stats['smallest_month']['year']}-{stats['smallest_month']['month']}"
        )
        lines.append(f"\n❄️ Smallest Month: {month_key}")
        lines.append(
            f"   Total: {format_kes(Decimal(stats['smallest_month']['total_commission']))}"
        )

    if stats["monthly_breakdown"]:
        lines.append("\n📊 Monthly Breakdown:")
        for month, data in sorted(stats["monthly_breakdown"].items()):
            lines.append(f"   {month}: {format_kes(data['total'])}")

    if stats["top_weeks"]:
        lines.append("\n🏆 Top 5 Weeks:")
        for week, total in stats["top_weeks"]:
            lines.append(f"   {week}: {format_kes(total)}")

    return "\n".join(lines)
