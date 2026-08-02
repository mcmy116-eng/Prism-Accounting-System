from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Role, AuditLog
from app import audit

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.active and user.check_password(password):
            login_user(user)
            audit.record("login", "auth", user.id, f"{user.name} logged in")
            db.session.commit()
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard.index"))
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/users")
@login_required
def users():
    if not current_user.is_admin():
        flash("Admins only.", "error")
        return redirect(url_for("dashboard.index"))
    all_users = User.query.order_by(User.created_at).all()
    return render_template("auth/users.html", users=all_users, roles=[r.value for r in Role])


@bp.route("/users/new", methods=["POST"])
@login_required
def new_user():
    if not current_user.is_admin():
        flash("Admins only.", "error")
        return redirect(url_for("dashboard.index"))
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", Role.VIEWER.value)
    password = request.form.get("password", "")
    if not name or not email or not password:
        flash("Name, email and password are required.", "error")
        return redirect(url_for("auth.users"))
    if User.query.filter_by(email=email).first():
        flash("A user with that email already exists.", "error")
        return redirect(url_for("auth.users"))
    u = User(name=name, email=email, role=role)
    u.set_password(password)
    db.session.add(u)
    db.session.flush()
    audit.record("create", "user", u.id, f"Created user {name} ({email}) as {role}")
    db.session.commit()
    flash(f"User {name} created.", "success")
    return redirect(url_for("auth.users"))


@bp.route("/audit")
@login_required
def audit_log():
    if not current_user.is_admin():
        flash("Admins only.", "error")
        return redirect(url_for("dashboard.index"))
    entity = request.args.get("entity", "")
    q = AuditLog.query
    if entity:
        q = q.filter_by(entity_type=entity)
    logs = q.order_by(AuditLog.at.desc()).limit(500).all()
    entities = [row[0] for row in db.session.query(AuditLog.entity_type).distinct().all()]
    return render_template("auth/audit.html", logs=logs, entities=entities, entity=entity)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle_user(user_id):
    if not current_user.is_admin():
        flash("Admins only.", "error")
        return redirect(url_for("dashboard.index"))
    u = User.query.get_or_404(user_id)
    if u.id == current_user.id:
        flash("You cannot deactivate yourself.", "error")
        return redirect(url_for("auth.users"))
    u.active = not u.active
    db.session.commit()
    return redirect(url_for("auth.users"))
