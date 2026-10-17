"""Household shopping list: one list shared by everyone in a family or shared house.

Adults add items straight to the list and decide requests. Children ask: their items wait as
requests until an adult approves or rejects them. Anyone can tick an item as bought.
No accounts. A member is a nickname plus a random token kept on their device. The join code is
the only way in, and new members get the household's default role (child in a family, adult in
a shared house). An adult can change anyone's role. All rules are checked here, not in the browser.
"""

import re
import secrets
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
KINDS = {"family": "child", "house": "adult"}      # kind -> role of new members
MAX_MEMBERS, MAX_OPEN_ITEMS = 12, 200
DIGITS = re.compile(r"\d{8,}")  # card and phone numbers never reach the database


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(text: str, limit: int, what: str) -> str:
    text = re.sub(r"\s+", " ", DIGITS.sub("", text)).strip()[:limit]
    if not text:
        raise HTTPException(400, f"Give a {what}.")
    return text


class NewHousehold(BaseModel):
    name: str
    member_name: str
    kind: str = "family"


class Join(BaseModel):
    code: str
    member_name: str


class NewItem(BaseModel):
    text: str


class ItemAction(BaseModel):
    action: str  # approve | reject | bought | unbought | remove


class MemberAction(BaseModel):
    action: str  # adult | child | remove


def make_router(conn: sqlite3.Connection) -> APIRouter:
    router = APIRouter(prefix="/api/household")

    def me(token: str | None) -> dict:
        row = token and conn.execute("SELECT * FROM household_members WHERE token = ?", (token,)).fetchone()
        if not row:
            raise HTTPException(401, "This device is not in a household. Start one or join with a code.")
        return dict(row)

    def adult(m: dict) -> None:
        if m["role"] != "adult":
            raise HTTPException(403, "Only an adult in the household can do that.")

    def item(m: dict, item_id: int) -> dict:
        row = conn.execute("SELECT * FROM household_items WHERE id = ? AND household_id = ?",
                           (item_id, m["household_id"])).fetchone()
        if not row:
            raise HTTPException(404, "That item is no longer on the list.")
        return dict(row)

    def add_member(household_id: int, name: str, role: str) -> str:
        token = secrets.token_urlsafe(24)
        conn.execute("INSERT INTO household_members (household_id, name, role, token, joined_on) VALUES (?,?,?,?,?)",
                     (household_id, name, role, token, _now()))
        return token

    def state(m: dict) -> dict:
        h = conn.execute("SELECT * FROM households WHERE id = ?", (m["household_id"],)).fetchone()
        members = [dict(r) for r in conn.execute(
            "SELECT id, name, role FROM household_members WHERE household_id = ? ORDER BY id", (h["id"],))]
        names = {x["id"]: x["name"] for x in members}
        items = []
        for r in conn.execute("SELECT * FROM household_items WHERE household_id = ? ORDER BY id", (h["id"],)):
            if r["status"] == "rejected" and r["added_by"] != m["id"]:
                continue  # only the person who asked sees a "no"
            items.append({"id": r["id"], "text": r["text"], "status": r["status"], "updated_at": r["updated_at"],
                          "mine": r["added_by"] == m["id"], "added_by": names.get(r["added_by"], "someone who left"),
                          "decided_by": names.get(r["decided_by"]), "bought_by": names.get(r["bought_by"])})
        return {"household": {"name": h["name"], "code": h["code"], "kind": h["kind"]},
                "me": {"id": m["id"], "name": m["name"], "role": m["role"]}, "members": members, "items": items}

    @router.post("")
    def create(body: NewHousehold):
        if body.kind not in KINDS:
            raise HTTPException(400, "kind must be family or house.")
        name = _clean(body.name, 40, "household name")
        member = _clean(body.member_name, 20, "nickname")
        for _ in range(5):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if not conn.execute("SELECT 1 FROM households WHERE code = ?", (code,)).fetchone():
                break
        cur = conn.execute("INSERT INTO households (code, name, kind, created_on) VALUES (?,?,?,?)",
                           (code, name, body.kind, _now()))
        token = add_member(cur.lastrowid, member, "adult")  # whoever starts it runs it
        conn.commit()
        return {"token": token, **state(me(token))}

    @router.post("/join")
    def join(body: Join):
        code = re.sub(r"[^A-Z0-9]", "", body.code.upper())
        h = conn.execute("SELECT * FROM households WHERE code = ?", (code,)).fetchone()
        if not h:
            raise HTTPException(404, "No household has that code. Check it with whoever shared it.")
        if conn.execute("SELECT COUNT(*) FROM household_members WHERE household_id = ?", (h["id"],)).fetchone()[0] \
                >= MAX_MEMBERS:
            raise HTTPException(409, f"This household is full ({MAX_MEMBERS} members).")
        token = add_member(h["id"], _clean(body.member_name, 20, "nickname"), KINDS[h["kind"]])
        conn.commit()
        return {"token": token, **state(me(token))}

    @router.get("")
    def get(x_member_token: str | None = Header(None)):
        return state(me(x_member_token))

    @router.post("/items")
    def add(body: NewItem, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        open_items = conn.execute("""SELECT COUNT(*) FROM household_items
                                     WHERE household_id = ? AND status IN ('requested', 'listed')""",
                                  (m["household_id"],)).fetchone()[0]
        if open_items >= MAX_OPEN_ITEMS:
            raise HTTPException(409, f"The list is full ({MAX_OPEN_ITEMS} items). Tick off or remove some first.")
        status = "listed" if m["role"] == "adult" else "requested"
        conn.execute("INSERT INTO household_items (household_id, text, status, added_by, updated_at) VALUES (?,?,?,?,?)",
                     (m["household_id"], _clean(body.text, 80, "item"), status, m["id"], _now()))
        conn.commit()
        return state(m)

    @router.post("/items/{item_id}")
    def act(item_id: int, body: ItemAction, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        i = item(m, item_id)
        a, s = body.action, i["status"]
        if a in ("approve", "reject"):
            adult(m)
            if s != "requested":
                raise HTTPException(409, "That request has already been decided.")
            conn.execute("UPDATE household_items SET status = ?, decided_by = ?, updated_at = ? WHERE id = ?",
                         ("listed" if a == "approve" else "rejected", m["id"], _now(), item_id))
        elif a in ("bought", "unbought"):
            if s not in ("listed", "bought"):
                raise HTTPException(409, "Only items on the list can be ticked off.")
            conn.execute("UPDATE household_items SET status = ?, bought_by = ?, updated_at = ? WHERE id = ?",
                         ("bought" if a == "bought" else "listed", m["id"] if a == "bought" else None, _now(), item_id))
        elif a == "remove":
            # adults remove anything; a child can withdraw or dismiss only their own request
            if m["role"] != "adult" and not (i["added_by"] == m["id"] and s in ("requested", "rejected")):
                raise HTTPException(403, "Only an adult can remove that.")
            conn.execute("DELETE FROM household_items WHERE id = ?", (item_id,))
        else:
            raise HTTPException(400, "action must be approve, reject, bought, unbought or remove.")
        conn.commit()
        return state(m)

    @router.post("/clear-bought")
    def clear_bought(x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        adult(m)
        conn.execute("DELETE FROM household_items WHERE household_id = ? AND status = 'bought'", (m["household_id"],))
        conn.commit()
        return state(m)

    @router.post("/members/{member_id}")
    def member(member_id: int, body: MemberAction, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        target = conn.execute("SELECT * FROM household_members WHERE id = ? AND household_id = ?",
                              (member_id, m["household_id"])).fetchone()
        if not target:
            raise HTTPException(404, "That person is not in this household.")
        if member_id != m["id"] or body.action != "remove":
            adult(m)  # anyone can leave; everything else needs an adult
        adults = conn.execute("SELECT COUNT(*) FROM household_members WHERE household_id = ? AND role = 'adult'",
                              (m["household_id"],)).fetchone()[0]
        last_adult = target["role"] == "adult" and adults == 1
        if body.action in ("adult", "child"):
            if last_adult and body.action == "child":
                raise HTTPException(409, "The household needs at least one adult. Make someone else an adult first.")
            conn.execute("UPDATE household_members SET role = ? WHERE id = ?", (body.action, member_id))
        elif body.action == "remove":
            others = conn.execute("SELECT COUNT(*) FROM household_members WHERE household_id = ? AND id != ?",
                                  (m["household_id"], member_id)).fetchone()[0]
            if last_adult and others:
                raise HTTPException(409, "The household needs at least one adult. Make someone else an adult first.")
            conn.execute("DELETE FROM household_members WHERE id = ?", (member_id,))
            if not others:  # last one out: nothing is left to keep
                conn.execute("DELETE FROM household_items WHERE household_id = ?", (m["household_id"],))
                conn.execute("DELETE FROM households WHERE id = ?", (m["household_id"],))
        else:
            raise HTTPException(400, "action must be adult, child or remove.")
        conn.commit()
        if member_id == m["id"] and body.action == "remove":
            return {"left": True}
        return state(me(x_member_token))

    return router
