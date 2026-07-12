"""AI-assisted extraction of vendor bills / receipts using the Anthropic API.

Extraction only ever produces a *draft* that a human reviews and approves
before anything is posted to the ledger (see bills.py review/approve flow).
"""
import base64
import json
import os
import mimetypes

EXTRACTION_MODEL = os.environ.get("EXTRACTION_MODEL", "claude-sonnet-5")

SYSTEM_PROMPT = """You extract structured data from vendor bills, receipts, and invoices \
for a bookkeeping system. Read the document carefully and return ONLY a JSON object \
(no prose, no markdown fences) with this exact shape:

{
  "vendor_name": string,
  "bill_date": "YYYY-MM-DD" or null,
  "due_date": "YYYY-MM-DD" or null,
  "currency_code": 3-letter ISO code, best guess (e.g. HKD, USD) or null,
  "vendor_reference": string or null,
  "subtotal": number or null,
  "tax": number or null,
  "total": number,
  "line_items": [
    {"description": string, "quantity": number, "unit_price": number, "amount": number, "category_guess": string}
  ]
}

Rules:
- All money values are plain decimal numbers, no currency symbols or thousands separators.
- If the document has no clear line-item breakdown, put a single line item covering the total.
- category_guess should be a short plain-English expense category guess (e.g. "Advertising",
  "Software subscription", "Shipping", "Office supplies") to help the bookkeeper pick a GL account.
- If a field is unreadable, use null. Never invent numbers.
"""


class ExtractionError(Exception):
    pass


def _media_type(filepath, mimetype_hint=None):
    if mimetype_hint:
        return mimetype_hint
    guessed, _ = mimetypes.guess_type(filepath)
    return guessed or "application/octet-stream"


def extract_bill_from_file(filepath: str, mimetype_hint: str = None) -> dict:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ExtractionError(
            "ANTHROPIC_API_KEY is not configured on the server. Ask an admin to set it, "
            "or enter this bill's details manually."
        )

    import anthropic

    media_type = _media_type(filepath, mimetype_hint)
    with open(filepath, "rb") as f:
        raw = f.read()
    b64 = base64.standard_b64encode(raw).decode("utf-8")

    if media_type == "application/pdf":
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": "application/pdf", "data": b64},
        }
    elif media_type in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        content_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        }
    else:
        raise ExtractionError(f"Unsupported file type for AI extraction: {media_type}")

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=EXTRACTION_MODEL,
            max_tokens=2000,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": "Extract this bill/receipt into the JSON schema described."},
                ],
            }],
        )
    except Exception as e:  # noqa: BLE001
        raise ExtractionError(f"AI extraction request failed: {e}")

    text = "".join(block.text for block in response.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"AI returned unparseable data: {e}")

    return data
