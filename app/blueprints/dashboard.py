from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from sqlalchemy import func

from flask_login import current_user

from app.extensions import db
from app.models import (
    Invoice, Bill, Account, AccountType, InvoiceStatus, BillStatus, JournalEntry,
    ExpenseClaim, ClaimStatus,
)

bp = Blueprint("dashboard", __name__, url_prefix="/")


@bp.route("/")
@login_required
def index():
    # Staff-only claimants have no visibility of company financials — send them
    # straight to their own claims.
    if current_user.is_staff_only():
        return redirect(url_for("claims.index"))

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

    pending_claims = ExpenseClaim.query.filter(
        ExpenseClaim.status.in_([ClaimStatus.PENDING_APPROVAL.value, ClaimStatus.SUBMITTED.value])
    ).order_by(ExpenseClaim.submitted_at).all()
    pending_claims_total = sum(c.total_cents for c in pending_claims)
    approved_unpaid = ExpenseClaim.query.filter_by(status=ClaimStatus.APPROVED.value).all()
    approved_unpaid_total = sum(c.balance_due_cents() for c in approved_unpaid)

    return render_template(
        "dashboard/index.html",
        mtd_revenue=mtd_revenue, mtd_expense=mtd_expense,
        total_ar=total_ar, total_ap=total_ap, total_cash=total_cash,
        overdue_invoices=overdue_invoices, recent_entries=recent_entries,
        net_income=mtd_revenue - mtd_expense,
        pending_claims=pending_claims, pending_claims_total=pending_claims_total,
        approved_unpaid_total=approved_unpaid_total,
    )
