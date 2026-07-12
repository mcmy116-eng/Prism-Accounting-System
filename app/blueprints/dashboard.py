from datetime import date, timedelta
from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models import Invoice, Bill, Account, AccountType, InvoiceStatus, BillStatus, JournalEntry

bp = Blueprint("dashboard", __name__, url_prefix="/")


@bp.route("/")
@login_required
def index():
    today = date.today()
    start_of_month = today.replace(day=1)

    revenue_accounts = Account.query.filter_by(type=AccountType.REVENUE.value).all()
    expense_accounts = Account.query.filter_by(type=AccountType.EXPENSE.value).all()

    mtd_revenue = sum(a.balance_cents(as_of=today) - a.balance_cents(as_of=start_of_month - timedelta(days=1))
                       for a in revenue_accounts)
    mtd_expense = sum(a.balance_cents(as_of=today) - a.balance_cents(as_of=start_of_month - timedelta(days=1))
                       for a in expense_accounts)

    total_ar = sum(i.balance_due_cents() for i in Invoice.query.filter(
        Invoice.status.in_([InvoiceStatus.SENT.value, InvoiceStatus.PARTIAL.value, InvoiceStatus.OVERDUE.value])
    ).all())
    total_ap = sum(b.balance_due_cents() for b in Bill.query.filter(
        Bill.status.in_([BillStatus.APPROVED.value, BillStatus.PARTIAL.value])
    ).all())

    overdue_invoices = Invoice.query.filter(
        Invoice.status.in_([InvoiceStatus.SENT.value, InvoiceStatus.PARTIAL.value]),
        Invoice.due_date < today,
    ).order_by(Invoice.due_date).limit(8).all()

    cash_accounts = Account.query.filter_by(is_bank=True, active=True).all()
    total_cash = sum(a.balance_cents(as_of=today) for a in cash_accounts)

    recent_entries = JournalEntry.query.order_by(JournalEntry.date.desc(), JournalEntry.id.desc()).limit(10).all()

    return render_template(
        "dashboard/index.html",
        mtd_revenue=mtd_revenue, mtd_expense=mtd_expense,
        total_ar=total_ar, total_ap=total_ap, total_cash=total_cash,
        overdue_invoices=overdue_invoices, recent_entries=recent_entries,
        net_income=mtd_revenue - mtd_expense,
    )
