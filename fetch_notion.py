import urllib.request, json, os
from datetime import datetime

token = os.environ["NOTION_TOKEN"]
outreach_db = os.environ["NOTION_DATABASE_ID"]
replies_db  = os.environ.get("NOTION_REPLIES_DATABASE_ID", "35dffa2025a84a03b4620946249883a4")

headers = {
    "Authorization": "Bearer " + token,
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def query_db(db_id):
    url = "https://api.notion.com/v1/databases/" + db_id + "/query"
    req = urllib.request.Request(url, data=b'{}', headers=headers, method='POST')
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get("results", [])

# ── Читаємо поточний data.json як базу (memory) ───────────────────────────────
existing = {"updated_at": "", "records": [], "replies": []}
if os.path.exists("data.json"):
    try:
        with open("data.json", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

# Індекс існуючих records: ключ = (account, date)
existing_records = {}
for r in existing.get("records", []):
    key = (r.get("account",""), r.get("date",""))
    existing_records[key] = r

# Індекс існуючих replies: ключ = profile_url
existing_replies = {}
for r in existing.get("replies", []):
    url = r.get("profile_url","")
    if url:
        existing_replies[url] = r

# ── Outreach stats з Notion ───────────────────────────────────────────────────
for page in query_db(outreach_db):
    p = page["properties"]
    num  = lambda k: (p.get(k,{}).get("number") or 0)
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    chk  = lambda k: p.get(k,{}).get("checkbox", False)
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    ttl  = lambda k: (p.get(k,{}).get("title") or [{}])[0].get("plain_text","")

    record = {
        "name":        ttl("Name"),
        "account":     sel("Account"),
        "date":        date("Date"),
        "processed":   num("Processed"),
        "accepted":    num("Accepted"),
        "messaged":    num("Messaged"),
        "replied":     num("Replied"),
        "failed":      num("Failed"),
        "is_baseline": chk("Is baseline")
    }

    key = (record["account"], record["date"])

    # Merge: якщо запис вже є і новий має нулі — залишаємо старий
    if key in existing_records:
        old = existing_records[key]
        # Оновлюємо тільки якщо нові дані не гірші
        if record["processed"] > 0 or record["is_baseline"]:
            existing_records[key] = record
        # Якщо новий processed=0 але старий мав дані — зберігаємо старий
        elif old.get("processed", 0) > 0:
            pass  # залишаємо старий
        else:
            existing_records[key] = record
    else:
        existing_records[key] = record

# ── Replies з Notion ──────────────────────────────────────────────────────────
for page in query_db(replies_db):
    p = page["properties"]
    txt  = lambda k: ((p.get(k,{}).get("rich_text") or [{}])[0].get("plain_text","") if p.get(k,{}).get("rich_text") else (p.get(k,{}).get("title") or [{}])[0].get("plain_text","") if p.get(k,{}).get("title") else "")
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    url  = lambda k: (p.get(k,{}).get("url") or "")
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))

    reply = {
        "name":         txt("Name"),
        "account":      sel("Account"),
        "company":      txt("Company"),
        "position":     txt("Position"),
        "profile_url":  url("Profile URL"),
        "their_reply":  txt("Their reply"),
        "our_last_message": txt("Our last message"),
        "status":       sel("Status"),
        "reply_date":   date("Reply date"),
    }

    profile_url = reply["profile_url"]
    if profile_url:
        existing_replies[profile_url] = reply  # завжди оновлюємо з Notion (статус міг змінитись)
    elif reply["name"]:
        # Без URL — зберігаємо по імені
        existing_replies[reply["name"]] = reply

# ── Збираємо фінальний data.json ──────────────────────────────────────────────
records = list(existing_records.values())
records.sort(key=lambda r: (r.get("date") or ""))

replies = list(existing_replies.values())
replies.sort(key=lambda r: r.get("reply_date") or "", reverse=True)

output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "records": records,
    "replies": replies
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Records: {len(records)} ({sum(1 for r in records if not r.get('is_baseline'))} live + {sum(1 for r in records if r.get('is_baseline'))} baseline)")
print(f"Replies: {len(replies)}")
