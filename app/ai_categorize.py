"""AI-assisted expense categorisation with a confidence score and a learning loop.

Given an expense line (merchant, description, plain-English category guess from
the receipt reader), this picks the most likely GL expense account and returns a
confidence in [0, 1]. Two signals feed the suggestion:

1. **Learned rules** — every time a human approves a categorisation we reinforce
   a keyword -> account rule (see ``learn``). Repeated confirmations raise the
   confidence of future matches. This is the "learns over time" behaviour.
2. **Name/keyword matching** — the receipt reader's plain-English guess (e.g.
   "Software subscription") is matched against the chart of accounts, plus a
   built-in keyword map for common SME expenses.

Nothing here posts to the ledger — it only proposes. A human always approves,
changes, or overrides the account before a claim is posted.
"""
import re

from app.extensions import db
from app.models import Account, CategoryRule

# Fallback account code when we genuinely can't tell.
FALLBACK_CODE = "6900"  # Miscellaneous Expense

# Built-in hints: substring found in merchant/description/guess -> account code.
# Deliberately conservative; the learned rules are what make this get smarter.
KEYWORD_HINTS = {
    "6000": ["advert", "facebook", "meta ads", "google ads", "tiktok", "paid media", "campaign"],
    "6010": ["software", "subscription", "saas", "adobe", "figma", "notion", "slack",
             "microsoft", "google workspace", "zoom", "canva", "openai", "anthropic"],
    "6040": ["rent", "utilit", "electric", "water bill", "gas bill"],
    "6050": ["office", "stationery", "supplies", "printer", "paper"],
    "6060": ["legal", "lawyer", "accountant", "audit", "consult", "professional fee"],
    "6070": ["taxi", "uber", "grab", "flight", "airline", "hotel", "meal", "restaurant",
             "lunch", "dinner", "coffee", "entertain", "travel", "mtr", "train", "parking"],
    "6080": ["bank fee", "transaction fee", "wire fee", "remittance"],
    "6100": ["insurance"],
    "6110": ["telephone", "mobile", "internet", "broadband", "sim", "data plan"],
    "5200": ["shipping", "courier", "postage", "freight", "sf express", "dhl", "fedex"],
    "5100": ["stripe fee", "paypal fee", "payment processing", "merchant fee"],
}

_TOKEN_RE = re.compile(r"[a-z0-9]{3,}")


def _tokens(*texts):
    seen = []
    for t in texts:
        if not t:
            continue
        for tok in _TOKEN_RE.findall(t.lower()):
            if tok not in seen:
                seen.append(tok)
    return seen


def _expense_accounts():
    return Account.query.filter(Account.type == "expense", Account.active == True).all()  # noqa: E712


def suggest_account(merchant="", description="", category_guess=""):
    """Return (account_id or None, confidence 0..1, reason)."""
    accounts_by_code = {a.code: a for a in _expense_accounts()}
    haystack = " ".join(t for t in (merchant, description, category_guess) if t).lower()
    tokens = _tokens(merchant, description, category_guess)

    # 1) Learned rules — strongest signal. Match any keyword token against learned rules.
    if tokens:
        rules = (CategoryRule.query
                 .filter(CategoryRule.keyword.in_(tokens))
                 .order_by(CategoryRule.hits.desc())
                 .all())
        # Also allow a learned rule whose keyword is a phrase contained in the haystack.
        phrase_rules = [r for r in CategoryRule.query.all()
                        if " " in r.keyword and r.keyword in haystack]
        best = None
        for r in rules + phrase_rules:
            if r.account and (best is None or r.hits > best.hits):
                best = r
        if best is not None:
            # Confidence climbs with reinforcement: 1 hit -> 0.72, 5+ -> ~0.95.
            confidence = min(0.95, 0.62 + 0.10 * min(best.hits, 4))
            return best.account_id, round(confidence, 2), f"learned from {best.hits} approval(s)"

    # 2) Built-in keyword hints.
    for code, needles in KEYWORD_HINTS.items():
        acct = accounts_by_code.get(code)
        if not acct:
            continue
        if any(n in haystack for n in needles):
            return acct.id, 0.6, "matched a common expense keyword"

    # 3) Fuzzy match the plain-English guess against account names.
    if category_guess:
        g = category_guess.lower()
        for a in accounts_by_code.values():
            name = a.name.lower()
            if g in name or name.split(" - ")[0] in g:
                return a.id, 0.5, "matched an account name"

    fallback = accounts_by_code.get(FALLBACK_CODE)
    return (fallback.id if fallback else None), 0.2, "no strong match — please confirm"


def learn(account_id, merchant="", description="", category_guess=""):
    """Reinforce keyword -> account rules from an approved categorisation."""
    if not account_id:
        return
    keywords = set()
    # Merchant is the highest-signal keyword; store the whole normalised merchant
    # plus its individual tokens.
    m = (merchant or "").strip().lower()
    if m:
        keywords.add(m[:120])
    for tok in _tokens(merchant, category_guess):
        keywords.add(tok)
    for kw in keywords:
        if not kw:
            continue
        rule = CategoryRule.query.filter_by(keyword=kw, account_id=account_id).first()
        if rule:
            rule.hits += 1
        else:
            db.session.add(CategoryRule(keyword=kw, account_id=account_id, hits=1))
