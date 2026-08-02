"""Seed the database with a default chart of accounts, reference data, and an
admin user. Safe to re-run - only inserts what's missing."""
import os
import sys

from app import create_app
from app.extensions import db
from app.models import (
    User, Role, Account, AccountType, Currency, TaxRate, CostCenter, CompanySettings,
)

CHART_OF_ACCOUNTS = [
    # code, name, type, subtype, is_bank, locked
    ("1000", "Cash and Cash Equivalents", "asset", None, False, True),
    ("1030", "Payment Processor Clearing (Stripe/Shopify/PayPal)", "asset", None, False, False),
    ("1100", "Accounts Receivable", "asset", None, False, True),
    ("1200", "Inventory", "asset", None, False, False),
    ("1300", "Prepaid Expenses", "asset", None, False, False),
    ("1400", "Fixed Assets - Equipment", "asset", None, False, False),
    ("1450", "Accumulated Depreciation", "asset", None, False, False),
    ("1500", "VAT / Tax Receivable", "asset", None, False, True),
    ("2000", "Accounts Payable", "liability", None, False, True),
    ("2100", "Credit Card Payable", "liability", None, False, False),
    ("2200", "VAT / Sales Tax Payable", "liability", None, False, True),
    ("2300", "Accrued Expenses", "liability", None, False, False),
    ("2400", "Deferred Revenue", "liability", None, False, False),
    ("2500", "Payroll Liabilities", "liability", None, False, False),
    ("2550", "Employee Reimbursements Payable", "liability", None, False, True),
    ("2600", "Loans Payable", "liability", None, False, False),
    ("3000", "Share Capital / Owner's Equity", "equity", None, False, True),
    ("3200", "Owner's Drawings / Dividends", "equity", None, False, False),
    ("4000", "E-commerce Sales Revenue", "revenue", None, False, False),
    ("4010", "Digital Marketing Service Revenue", "revenue", None, False, False),
    ("4100", "Shipping Income", "revenue", None, False, False),
    ("4200", "Other Income", "revenue", None, False, False),
    ("4900", "Sales Returns & Allowances", "revenue", None, False, False),
    ("4950", "Sales Discounts", "revenue", None, False, False),
    ("5000", "Cost of Goods Sold - Products", "expense", "cogs", False, False),
    ("5100", "Merchant / Payment Processing Fees", "expense", "cogs", False, False),
    ("5200", "Shipping & Fulfillment Costs", "expense", "cogs", False, False),
    ("5300", "Platform / Marketplace Fees", "expense", "cogs", False, False),
    ("5400", "Contractor Costs - Client Delivery", "expense", "cogs", False, False),
    ("6000", "Advertising & Paid Media", "expense", None, False, False),
    ("6010", "Software & Subscriptions", "expense", None, False, False),
    ("6020", "Salaries & Wages", "expense", None, False, False),
    ("6030", "Contractor / Freelancer Expenses", "expense", None, False, False),
    ("6040", "Rent & Utilities", "expense", None, False, False),
    ("6050", "Office Supplies", "expense", None, False, False),
    ("6060", "Professional Fees (Legal/Accounting)", "expense", None, False, False),
    ("6070", "Travel & Entertainment", "expense", None, False, False),
    ("6080", "Bank & Transaction Fees", "expense", None, False, False),
    ("6090", "Depreciation Expense", "expense", None, False, False),
    ("6100", "Insurance", "expense", None, False, False),
    ("6110", "Telephone & Internet", "expense", None, False, False),
    ("6900", "Miscellaneous Expense", "expense", None, False, False),
]

CURRENCIES = [
    ("HKD", "Hong Kong Dollar", "$"),
    ("USD", "US Dollar", "$"),
    ("CNY", "Chinese Yuan", "¥"),
    ("EUR", "Euro", "€"),
    ("GBP", "British Pound", "£"),
    ("JPY", "Japanese Yen", "¥"),
]

TAX_RATES = [
    ("No Tax", 0.0),
    ("HK Standard (0%)", 0.0),
]

COST_CENTERS = [
    ("ECOM", "E-commerce"),
    ("DIGI", "Digital Marketing Services"),
    ("ADMIN", "General & Admin"),
]


def seed():
    app = create_app()
    with app.app_context():
        db.create_all()

        for code, name, symbol in CURRENCIES:
            if not Currency.query.get(code):
                db.session.add(Currency(code=code, name=name, symbol=symbol))

        if not CompanySettings.query.first():
            db.session.add(CompanySettings(company_name="Prism Group International Limited"))

        for code, name, type_, subtype, is_bank, locked in CHART_OF_ACCOUNTS:
            if not Account.query.filter_by(code=code).first():
                db.session.add(Account(code=code, name=name, type=type_, subtype=subtype,
                                        is_bank=is_bank, system_locked=locked))

        for name, rate in TAX_RATES:
            if not TaxRate.query.filter_by(name=name).first():
                db.session.add(TaxRate(name=name, rate=rate))

        for code, name in COST_CENTERS:
            if not CostCenter.query.filter_by(code=code).first():
                db.session.add(CostCenter(code=code, name=name))

        db.session.commit()

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@prism-hk.com")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if not User.query.filter_by(email=admin_email).first():
            if not admin_password:
                print("ERROR: Set ADMIN_PASSWORD env var to create the first admin user, e.g.")
                print("  ADMIN_EMAIL=you@example.com ADMIN_PASSWORD='changeme123' python3 seed.py")
                sys.exit(1)
            admin = User(name="Admin", email=admin_email, role=Role.ADMIN.value)
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin user: {admin_email}")
        else:
            print(f"Admin user {admin_email} already exists, skipping.")

        print("Seed complete.")


if __name__ == "__main__":
    seed()
