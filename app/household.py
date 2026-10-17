"""Household shopping list: one list shared by everyone in a home, run like a group chat.

Three roles. The owner started the household: there is one, and nobody can remove them.
Admins make or dismiss other admins and remove anyone but the owner. Members add to the list,
tick items off and remove what they added. Admins can remove any item and clear bought ones.
Anyone can claim an item ("I'm getting this") so others see it and nobody buys it twice. A claim ends
when the item is bought, when its claimer lets it go or leaves, or after CLAIM_HOURS.
No accounts. A member is a nickname plus a random token kept on their device. The join code is
the only way in, and everyone joins as a member. All rules are checked here, not in the browser.
"""

import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L
MAX_MEMBERS, MAX_OPEN_ITEMS = 12, 200
DIGITS = re.compile(r"\d{8,}")  # card and phone numbers never reach the database


CLAIM_HOURS = 24  # "I'm getting this" lapses after a day, so a forgotten claim never blocks anyone


def _claim_live(r) -> bool:
    return bool(r["claimed_by"] and r["claimed_at"] and
                datetime.fromisoformat(r["claimed_at"]) > datetime.now(timezone.utc) - timedelta(hours=CLAIM_HOURS))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _clean(text: str, limit: int, what: str) -> str:
    text = re.sub(r"\s+", " ", DIGITS.sub("", text)).strip()[:limit]
    if not text:
        raise HTTPException(400, f"Give a {what}.")
    return text


def _manages(m: dict, target: dict) -> bool:
    """The owner manages everyone else, an admin manages everyone but the owner."""
    return m["id"] != target["id"] and (m["role"] == "owner" or (m["role"] == "admin" and target["role"] != "owner"))


class NewHousehold(BaseModel):
    name: str
    member_name: str


class Join(BaseModel):
    code: str
    member_name: str


class NewItem(BaseModel):
    text: str


class ItemAction(BaseModel):
    action: str  # bought | unbought | remove


class MemberAction(BaseModel):
    action: str  # admin | member | remove


def make_router(conn: sqlite3.Connection) -> APIRouter:
    router = APIRouter(prefix="/api/household")

    def me(token: str | None) -> dict:
        row = token and conn.execute("SELECT * FROM household_members WHERE token = ?", (token,)).fetchone()
        if not row:
            raise HTTPException(401, "This device is not in a household. Start one or join with a code.")
        return dict(row)

    def admin(m: dict) -> None:
        if m["role"] not in ("owner", "admin"):
            raise HTTPException(403, "Only an admin can do that.")

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
        for x in members:
            x["manage"] = _manages(m, x)
        names = {x["id"]: x["name"] for x in members}
        is_admin = m["role"] in ("owner", "admin")
        items = []
        for r in conn.execute("SELECT * FROM household_items WHERE household_id = ? ORDER BY id", (h["id"],)):
            claim = r["status"] == "listed" and _claim_live(r) and r["claimed_by"] in names  # left: claim gone
            items.append({"id": r["id"], "text": r["text"], "status": r["status"], "updated_at": r["updated_at"],
                          "mine": r["added_by"] == m["id"], "added_by": names.get(r["added_by"], "someone who left"),
                          "bought_by": names.get(r["bought_by"]), "can_remove": is_admin or r["added_by"] == m["id"],
                          "claimed_by": names[r["claimed_by"]] if claim else None,
                          "claimed_mine": claim and r["claimed_by"] == m["id"]})
        return {"household": {"name": h["name"], "code": h["code"]},
                "me": {"id": m["id"], "name": m["name"], "role": m["role"]}, "members": members, "items": items}

    @router.post("")
    def create(body: NewHousehold):
        name = _clean(body.name, 40, "household name")
        member = _clean(body.member_name, 20, "nickname")
        for _ in range(5):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if not conn.execute("SELECT 1 FROM households WHERE code = ?", (code,)).fetchone():
                break
        cur = conn.execute("INSERT INTO households (code, name, created_on) VALUES (?,?,?)", (code, name, _now()))
        token = add_member(cur.lastrowid, member, "owner")
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
        token = add_member(h["id"], _clean(body.member_name, 20, "nickname"), "member")
        conn.commit()
        return {"token": token, **state(me(token))}

    @router.get("")
    def get(x_member_token: str | None = Header(None)):
        return state(me(x_member_token))

    @router.post("/items")
    def add(body: NewItem, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        open_items = conn.execute("SELECT COUNT(*) FROM household_items WHERE household_id = ? AND status = 'listed'",
                                  (m["household_id"],)).fetchone()[0]
        if open_items >= MAX_OPEN_ITEMS:
            raise HTTPException(409, f"The list is full ({MAX_OPEN_ITEMS} items). Tick off or remove some first.")
        conn.execute("INSERT INTO household_items (household_id, text, status, added_by, updated_at) VALUES (?,?,?,?,?)",
                     (m["household_id"], _clean(body.text, 80, "item"), "listed", m["id"], _now()))
        conn.commit()
        return state(m)

    @router.post("/items/{item_id}")
    def act(item_id: int, body: ItemAction, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        i = item(m, item_id)
        if body.action in ("bought", "unbought"):
            bought = body.action == "bought"  # either way the claim is done with
            conn.execute("""UPDATE household_items SET status = ?, bought_by = ?, claimed_by = NULL, claimed_at = NULL,
                            updated_at = ? WHERE id = ?""",
                         ("bought" if bought else "listed", m["id"] if bought else None, _now(), item_id))
        elif body.action == "claim":
            if i["status"] != "listed":
                raise HTTPException(409, "That item has already been bought.")
            if _claim_live(i) and i["claimed_by"] != m["id"]:
                who = conn.execute("SELECT name FROM household_members WHERE id = ?", (i["claimed_by"],)).fetchone()
                if who:
                    raise HTTPException(409, f"{who['name']} is already getting {i['text']}.")
            conn.execute("UPDATE household_items SET claimed_by = ?, claimed_at = ? WHERE id = ?", (m["id"], _now(), item_id))
        elif body.action == "unclaim":
            if _claim_live(i) and i["claimed_by"] != m["id"]:
                admin(m)  # an admin can free an item someone else claimed
            conn.execute("UPDATE household_items SET claimed_by = NULL, claimed_at = NULL WHERE id = ?", (item_id,))
        elif body.action == "remove":
            if i["added_by"] != m["id"]:
                admin(m)  # members remove only what they added
            conn.execute("DELETE FROM household_items WHERE id = ?", (item_id,))
        else:
            raise HTTPException(400, "action must be bought, unbought, claim, unclaim or remove.")
        conn.commit()
        return state(m)

    @router.post("/clear-bought")
    def clear_bought(x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        admin(m)
        conn.execute("DELETE FROM household_items WHERE household_id = ? AND status = 'bought'", (m["household_id"],))
        conn.commit()
        return state(m)

    @router.post("/members/{member_id}")
    def member(member_id: int, body: MemberAction, x_member_token: str | None = Header(None)):
        m = me(x_member_token)
        row = conn.execute("SELECT * FROM household_members WHERE id = ? AND household_id = ?",
                           (member_id, m["household_id"])).fetchone()
        if not row:
            raise HTTPException(404, "That person is not in this household.")
        target, leaving = dict(row), member_id == m["id"] and body.action == "remove"
        if body.action not in ("admin", "member", "remove"):
            raise HTTPException(400, "action must be admin, member or remove.")
        if not leaving:  # anyone can leave; everything else is an admin acting on someone else
            admin(m)
            if not _manages(m, target):
                raise HTTPException(403, "Nobody can remove the owner or change their role."
                                    if target["role"] == "owner" else "You cannot change your own role.")
        if body.action in ("admin", "member"):
            conn.execute("UPDATE household_members SET role = ? WHERE id = ?", (body.action, member_id))
        else:
            conn.execute("DELETE FROM household_members WHERE id = ?", (member_id,))
            heir = conn.execute("""SELECT id FROM household_members WHERE household_id = ?
                                   ORDER BY role = 'admin' DESC, id LIMIT 1""", (m["household_id"],)).fetchone()
            if not heir:  # last one out: nothing is left to keep
                conn.execute("DELETE FROM household_items WHERE household_id = ?", (m["household_id"],))
                conn.execute("DELETE FROM households WHERE id = ?", (m["household_id"],))
            elif target["role"] == "owner":  # the owner left: the longest-serving admin, else member, takes over
                conn.execute("UPDATE household_members SET role = 'owner' WHERE id = ?", (heir["id"],))
        conn.commit()
        if leaving:
            return {"left": True}
        return state(me(x_member_token))

    return router
