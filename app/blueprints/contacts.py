from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Contact, ContactType, Invoice, Bill

bp = Blueprint("contacts", __name__, url_prefix="/contacts")


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    query = Contact.query.filter_by(active=True)
    if q:
        query = query.filter(Contact.name.ilike(f"%{q}%"))
    contacts = query.order_by(Contact.name).all()
    return render_template("contacts/index.html", contacts=contacts, q=q, types=[t.value for t in ContactType])


@bp.route("/new", methods=["POST"])
@login_required
def new():
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("contacts.index"))
    name = request.form.get("name", "").strip()
    if not name:
        flash("Name is required.", "error")
        return redirect(url_for("contacts.index"))
    c = Contact(
        name=name,
        type=request.form.get("type", ContactType.CUSTOMER.value),
        email=request.form.get("email", "").strip(),
        phone=request.form.get("phone", "").strip(),
        address=request.form.get("address", "").strip(),
        currency_code=request.form.get("currency_code", "HKD"),
        tax_id=request.form.get("tax_id", "").strip(),
        notes=request.form.get("notes", "").strip(),
    )
    db.session.add(c)
    db.session.commit()
    flash(f"Contact {name} created.", "success")
    return redirect(url_for("contacts.index"))


@bp.route("/<int:contact_id>")
@login_required
def detail(contact_id):
    c = Contact.query.get_or_404(contact_id)
    invoices = Invoice.query.filter_by(contact_id=contact_id).order_by(Invoice.issue_date.desc()).all()
    bills = Bill.query.filter_by(contact_id=contact_id).order_by(Bill.bill_date.desc()).all()
    return render_template("contacts/detail.html", contact=c, invoices=invoices, bills=bills)


@bp.route("/<int:contact_id>/archive", methods=["POST"])
@login_required
def archive(contact_id):
    if not current_user.can_edit():
        flash("You don't have permission to do that.", "error")
        return redirect(url_for("contacts.index"))
    c = Contact.query.get_or_404(contact_id)
    c.active = False
    db.session.commit()
    flash(f"{c.name} archived.", "success")
    return redirect(url_for("contacts.index"))
