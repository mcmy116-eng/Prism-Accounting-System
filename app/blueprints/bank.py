import csv
import io
import uuid
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import BankAccount, BankTransaction, Account, AccountType, JournalLine, JournalEntry, cents
from app.ledger import create_journal_entry, LedgerError
from app.system_accounts import get_system_account

bp = Blueprint("bank", __name__, url_prefix="/bank")


@bp.route("/")
@login_required
def index():
    accounts = BankAccount.query.filter_by(active=True).all()
    balances = {a.id: a.gl_account.balance_cents(as_of=date.today()) for a in accounts}
    return render_template("bank/index.html", accounts=accounts, balances=balances)


@bp.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("bank.index"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "error")
            return redirect(url_for("bank.new"))
        code_base = 1010
        existing_codes = {int(a.code) for a in Account.query.filter(Account.code.between("1000", "1099")).all() if a.code.isdigit()}
        code = code_base
        while str(code) in {str(c) for c in existing_codes}:
            code += 1
        gl = Account(code=str(code), name=f"{name} (Bank)", type=AccountType.ASSET.value, is_bank=True)
        db.session.add(gl)
        db.session.flush()

        opening = cents(request.form.get("opening_balance") or 0)
        bank = BankAccount(
            name=name, account_number=request.form.get("account_number", ""),
            currency_code=request.form.get("currency_code", "HKD"),
            gl_account_id=gl.id, opening_balance_cents=opening,
        )
        db.session.add(bank)
        db.session.flush()

        if opening:
            equity = Account.query.filter_by(code="3000").first()
            create_journal_entry(
                date.today(), f"Opening balance for {name}",
                [
                    {"account_id": gl.id, "debit_cents": opening, "credit_cents": 0, "description": "Opening balance"},
                    {"account_id": equity.id, "debit_cents": 0, "credit_cents": opening, "description": "Opening balance"},
                ],
                source_type="manual", created_by_id=current_user.id,
            )
        db.session.commit()
        flash(f"Bank account {name} created.", "success")
        return redirect(url_for("bank.index"))
    return render_template("bank/new.html")


@bp.route("/<int:bank_id>")
@login_required
def detail(bank_id):
    bank = BankAccount.query.get_or_404(bank_id)
    transactions = BankTransaction.query.filter_by(bank_account_id=bank_id).order_by(BankTransaction.date.desc()).all()
    return render_template("bank/detail.html", bank=bank, transactions=transactions)


@bp.route("/<int:bank_id>/import", methods=["POST"])
@login_required
def import_csv(bank_id):
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("bank.detail", bank_id=bank_id))
    bank = BankAccount.query.get_or_404(bank_id)
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Choose a CSV file.", "error")
        return redirect(url_for("bank.detail", bank_id=bank_id))

    content = file.stream.read().decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(content))
    fieldnames_lower = {f.lower().strip(): f for f in (reader.fieldnames or [])}

    date_key = next((fieldnames_lower[k] for k in fieldnames_lower if "date" in k), None)
    desc_key = next((fieldnames_lower[k] for k in fieldnames_lower if "desc" in k or "memo" in k or "narrative" in k), None)
    amount_key = next((fieldnames_lower[k] for k in fieldnames_lower if k == "amount"), None)
    debit_key = next((fieldnames_lower[k] for k in fieldnames_lower if "debit" in k or "withdrawal" in k or "out" in k), None)
    credit_key = next((fieldnames_lower[k] for k in fieldnames_lower if "credit" in k or "deposit" in k or "in" == k), None)

    if not date_key or (not amount_key and not (debit_key or credit_key)):
        flash("Couldn't detect date/amount columns. Expected headers like Date, Description, Amount "
              "(or Date, Description, Debit, Credit).", "error")
        return redirect(url_for("bank.detail", bank_id=bank_id))

    batch = uuid.uuid4().hex[:10]
    count = 0
    for row in reader:
        raw_date = (row.get(date_key) or "").strip()
        if not raw_date:
            continue
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue
        if not parsed_date:
            continue

        if amount_key:
            amt = cents(row.get(amount_key) or 0)
        else:
            debit = cents(row.get(debit_key) or 0) if debit_key else 0
            credit = cents(row.get(credit_key) or 0) if credit_key else 0
            amt = credit - debit

        desc = (row.get(desc_key) or "").strip() if desc_key else ""
        db.session.add(BankTransaction(
            bank_account_id=bank.id, date=parsed_date, description=desc,
            amount_cents=amt, import_batch=batch, status="unmatched",
        ))
        count += 1
    db.session.commit()
    flash(f"Imported {count} transactions.", "success")
    return redirect(url_for("bank.detail", bank_id=bank_id))


@bp.route("/<int:bank_id>/reconcile")
@login_required
def reconcile(bank_id):
    bank = BankAccount.query.get_or_404(bank_id)
    unmatched_txns = BankTransaction.query.filter_by(bank_account_id=bank_id, status="unmatched").order_by(BankTransaction.date).all()
    matched_line_ids = {jl.id for jl in JournalLine.query.filter_by(account_id=bank.gl_account_id).all()}
    already_linked = {bt.matched_journal_line_id for bt in BankTransaction.query.filter(BankTransaction.matched_journal_line_id.isnot(None)).all()}
    candidate_lines = (JournalLine.query.join(JournalEntry)
                        .filter(JournalLine.account_id == bank.gl_account_id, JournalEntry.is_posted == True)  # noqa: E712
                        .order_by(JournalEntry.date.desc()).all())
    candidate_lines = [l for l in candidate_lines if l.id not in already_linked]
    all_accounts = Account.query.filter_by(active=True).order_by(Account.code).all()
    return render_template("bank/reconcile.html", bank=bank, unmatched_txns=unmatched_txns,
                            candidate_lines=candidate_lines, all_accounts=all_accounts)


@bp.route("/<int:bank_id>/match", methods=["POST"])
@login_required
def match(bank_id):
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("bank.reconcile", bank_id=bank_id))
    txn_id = int(request.form["txn_id"])
    line_id = int(request.form["line_id"])
    txn = BankTransaction.query.get_or_404(txn_id)
    txn.matched_journal_line_id = line_id
    txn.status = "matched"
    db.session.commit()
    flash("Transaction matched.", "success")
    return redirect(url_for("bank.reconcile", bank_id=bank_id))


@bp.route("/<int:bank_id>/quick-entry", methods=["POST"])
@login_required
def quick_entry(bank_id):
    """For bank transactions with no matching source doc (e.g. bank fees, interest) -
    post a two-sided journal entry directly and mark the transaction matched."""
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("bank.reconcile", bank_id=bank_id))
    bank = BankAccount.query.get_or_404(bank_id)
    txn_id = int(request.form["txn_id"])
    contra_account_id = int(request.form["contra_account_id"])
    txn = BankTransaction.query.get_or_404(txn_id)

    amount = abs(txn.amount_cents)
    if txn.amount_cents >= 0:
        lines = [
            {"account_id": bank.gl_account_id, "debit_cents": amount, "credit_cents": 0, "description": txn.description},
            {"account_id": contra_account_id, "debit_cents": 0, "credit_cents": amount, "description": txn.description},
        ]
    else:
        lines = [
            {"account_id": contra_account_id, "debit_cents": amount, "credit_cents": 0, "description": txn.description},
            {"account_id": bank.gl_account_id, "debit_cents": 0, "credit_cents": amount, "description": txn.description},
        ]
    try:
        entry = create_journal_entry(txn.date, txn.description or "Bank transaction", lines,
                                      source_type="bank", source_id=txn.id, created_by_id=current_user.id)
    except LedgerError as e:
        flash(str(e), "error")
        return redirect(url_for("bank.reconcile", bank_id=bank_id))

    bank_line = next(l for l in entry.lines if l.account_id == bank.gl_account_id)
    txn.matched_journal_line_id = bank_line.id
    txn.status = "matched"
    db.session.commit()
    flash("Entry posted and matched.", "success")
    return redirect(url_for("bank.reconcile", bank_id=bank_id))


@bp.route("/<int:bank_id>/reconcile-line/<int:line_id>", methods=["POST"])
@login_required
def reconcile_line(bank_id, line_id):
    txn = BankTransaction.query.filter_by(matched_journal_line_id=line_id).first()
    if txn:
        txn.status = "reconciled"
        db.session.commit()
    return redirect(url_for("bank.reconcile", bank_id=bank_id))
