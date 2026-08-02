"""Lookup helpers for the fixed system accounts that ledger postings rely on.

These codes are created by seed.py and must not be renumbered without updating
the SYSTEM_CODES map below.
"""
from app.models import Account

SYSTEM_CODES = {
    "1100": "Accounts Receivable",
    "2000": "Accounts Payable",
    "2200": "VAT / Sales Tax Payable",
    "1500": "VAT / Tax Receivable",
    "2550": "Employee Reimbursements Payable",
}


class MissingSystemAccount(Exception):
    pass


def get_system_account(code: str) -> Account:
    a = Account.query.filter_by(code=code).first()
    if not a:
        raise MissingSystemAccount(
            f"Required system account {code} is missing. Run the seed script."
        )
    return a
