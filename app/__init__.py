import os
from flask import Flask
from app.extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.environ.get("DATABASE_PATH", os.path.join(basedir, "instance", "accounting.db"))
    database_url = os.environ.get("DATABASE_URL", f"sqlite:///{db_path}")
    # Railway/Render/Heroku-style providers hand out "postgres://", but SQLAlchemy 2.x requires "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["UPLOAD_FOLDER"] = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(basedir, "uploads")
    )
    app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20MB uploads

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.accounts import bp as accounts_bp
    from app.blueprints.contacts import bp as contacts_bp
    from app.blueprints.invoices import bp as invoices_bp
    from app.blueprints.bills import bp as bills_bp
    from app.blueprints.payments import bp as payments_bp
    from app.blueprints.bank import bp as bank_bp
    from app.blueprints.reports import bp as reports_bp
    from app.blueprints.settings import bp as settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(bank_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    from app.models import money as money_fn
    app.jinja_env.filters["money"] = money_fn

    @app.context_processor
    def inject_globals():
        from app.models import CompanySettings
        settings = CompanySettings.query.first()
        return {"company_settings": settings}

    return app
