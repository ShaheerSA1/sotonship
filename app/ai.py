"""Claude calls: read a receipt, and match a free-text shopping list to the catalogue."""

import base64
import json
import os
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel

from .db import DATA

MODEL = os.environ.get("MODEL") or "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]

IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class AIUnavailable(Exception):
    """No credentials, network down, or the API refused. Shown to the user as is."""


# ---------- schemas ----------

class ReceiptLine(BaseModel):
    raw_text: str
    quantity: float
    line_total: float
    unit_price: float
    loyalty_discount: Optional[float]
    loyalty_scheme: Optional[str]
    product_id: Optional[str]
    confidence: Literal["high", "medium", "low"]


class Receipt(BaseModel):
    is_receipt: bool
    reason_if_not: Optional[str]
    chain: Optional[str]
    store_postcode: Optional[str]
    purchase_date: Optional[str]
    lines: list[ReceiptLine]
    total: Optional[float]


class ListItem(BaseModel):
    input_text: str
    quantity: int
    status: Literal["matched", "ambiguous", "not_in_catalogue"]
    generic: Optional[str]
    brand: Optional[str]
    product_ids: list[str]
    options: list[str]
    note: str


class ShoppingList(BaseModel):
    items: list[ListItem]


# ---------- prompts ----------

def _catalogue_block(catalogue: list[dict]) -> str:
    return "\n".join(f"{p['id']} | {p['name']} | brand: {p['brand']} | group: {p['generic']}" for p in catalogue)


def _tuning_examples() -> str:
    path = DATA / "eval" / "receipt_lines_tune.json"
    rows = json.loads(path.read_text())["lines"]
    return "\n".join(f"{r['chain']}: \"{r['raw']}\" -> {r['product_id']}" for r in rows)


RECEIPT_SYSTEM = """You read UK supermarket receipts (photos, PDFs, pasted e-receipts) for a community grocery price database.

Extract every purchased product line. For each line:
- raw_text: the product text as printed, with any long digit strings removed.
- quantity, line_total, unit_price: unit_price is the shelf price of one unit before loyalty savings. For "2 @ £1.25" the quantity is 2 and unit_price 1.25.
- loyalty_discount: if a loyalty line follows the item (e.g. "Clubcard Price Saving -0.75", "Nectar Price -0.50", "Lidl Plus coupon"), the saving per unit as a positive number, and loyalty_scheme names the scheme. Otherwise null.
- product_id: the catalogue id below, only when the line is the same product. Any supermarket's own label maps to the brand "own" product. A branded line maps only to that brand. Size must match within about 10 percent. If nothing fits, null. Do not guess.
- confidence: how sure you are of the product_id mapping (low if the abbreviation is unclear).

Skip carrier bags, deposits, totals, payment lines, cashback and coupons that are not tied to one item.
chain: one of Tesco, Sainsbury's, Asda, Lidl, Aldi, Morrisons, Co-op, M&S, Iceland, or "other". store_postcode if printed. purchase_date as YYYY-MM-DD if printed.
If the input is not a shop receipt, set is_receipt false, explain in reason_if_not, and return no lines.

Privacy: never output card numbers, loyalty card numbers, names, email addresses, or anything else that identifies the shopper. The schema has no place for them.

Examples of mapping receipt abbreviations:
{examples}

Catalogue:
{catalogue}"""

LIST_SYSTEM = """You turn a shopper's free-text grocery list into catalogue products, so a planner can price the list across local shops.

Split the input into separate items. For each item return:
- input_text: the item as the shopper wrote it. quantity: how many (default 1).
- status "matched": generic is the catalogue group. product_ids lists every catalogue id the shopper would accept. If they named a brand, set brand and only include that brand's products. If they did not name a brand, include all brands in the group, own label too.
- status "ambiguous": the item could be several different groups (e.g. "crisps" without a flavour). options lists the candidate groups, product_ids is empty.
- status "not_in_catalogue": we do not track it (non-grocery items, or groceries missing from the catalogue). product_ids empty. Say so plainly in note.
- note: one short sentence, e.g. which sizes we track ("only 1kg basmati tracked").

Never invent ids. Only use ids from the catalogue below.

Catalogue:
{catalogue}"""


# ---------- calls ----------

def _client() -> anthropic.Anthropic:
    try:
        return anthropic.Anthropic()
    except Exception as e:  # missing credentials raise at construction in some setups
        raise AIUnavailable(f"No Anthropic credentials: {e}") from e


def _call(system: str, content: list[dict], schema: type[BaseModel], effort: str):
    try:
        response = _client().beta.messages.parse(
            model=MODEL,
            max_tokens=16000,
            betas=BETAS,
            fallbacks="default",
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort},
            output_format=schema,
        )
    except anthropic.AuthenticationError as e:
        raise AIUnavailable("Anthropic API key missing or invalid. Set ANTHROPIC_API_KEY in .env.") from e
    except anthropic.RateLimitError as e:
        raise AIUnavailable("Anthropic rate limit hit. Try again in a minute.") from e
    except anthropic.BadRequestError as e:
        raise AIUnavailable(f"Anthropic rejected the request: {e.message}") from e
    except anthropic.APIStatusError as e:
        raise AIUnavailable(f"Anthropic API error {e.status_code}. Request id {e.request_id}.") from e
    except anthropic.APIConnectionError as e:
        raise AIUnavailable("Cannot reach the Anthropic API (network).") from e
    except TypeError as e:  # raised by the SDK when no credentials resolve at all
        raise AIUnavailable(f"No Anthropic credentials: {e}") from e
    if response.stop_reason == "refusal":
        raise AIUnavailable("The model declined this input.")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise AIUnavailable("The model output was cut off or did not parse.")
    return response.parsed_output


def parse_receipt(data: bytes, media_type: str, catalogue: list[dict]) -> Receipt:
    if media_type in IMAGE_TYPES:
        block = {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.standard_b64encode(data).decode()}}
    elif media_type == "application/pdf":
        block = {"type": "document", "source": {"type": "base64", "media_type": media_type,
                                                "data": base64.standard_b64encode(data).decode()}}
    elif media_type.startswith("text/"):
        block = {"type": "text", "text": data.decode("utf-8", errors="replace")}
    else:
        raise ValueError(f"Unsupported file type {media_type}. Use JPG, PNG, WEBP, PDF or text.")
    system = RECEIPT_SYSTEM.format(examples=_tuning_examples(), catalogue=_catalogue_block(catalogue))
    receipt = _call(system, [block, {"type": "text", "text": "Read this receipt."}], Receipt, "medium")
    ids = {p["id"] for p in catalogue}
    for line in receipt.lines:
        if line.product_id not in ids:
            line.product_id = None
    return receipt


def match_list(text: str, catalogue: list[dict]) -> list[dict]:
    system = LIST_SYSTEM.format(catalogue=_catalogue_block(catalogue))
    result = _call(system, [{"type": "text", "text": text}], ShoppingList, "low")
    ids = {p["id"] for p in catalogue}
    items = []
    for item in result.items:
        d = item.model_dump()
        d["product_ids"] = [i for i in d["product_ids"] if i in ids]
        if d["status"] == "matched" and not d["product_ids"]:
            d["status"], d["note"] = "not_in_catalogue", d["note"] or "no valid catalogue id returned"
        items.append(d)
    return items
