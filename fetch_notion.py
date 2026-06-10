import urllib.request, json, os
from datetime import datetime

token = os.environ["NOTION_TOKEN"]
outreach_db  = os.environ["NOTION_DATABASE_ID"]
replies_db   = os.environ.get("NOTION_REPLIES_DATABASE_ID",  "35dffa2025a84a03b4620946249883a4")
crm_db       = os.environ.get("NOTION_CRM_DATABASE_ID",      "baabe99c2838447482e4c9356ad70610")

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

# ── Читаємо поточний data.json (memory) ──────────────────────────────────────
existing = {"updated_at": "", "records": [], "replies": [], "crm": []}
if os.path.exists("data.json"):
    try:
        with open("data.json", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        pass

existing_records = {}
for r in existing.get("records", []):
    key = (r.get("account",""), r.get("date",""))
    existing_records[key] = r

existing_replies = {}
for r in existing.get("replies", []):
    key = r.get("profile_url","") or r.get("name","")
    if key:
        existing_replies[key] = r

# ── Outreach stats ────────────────────────────────────────────────────────────
for page in query_db(outreach_db):
    p = page["properties"]
    num  = lambda k: (p.get(k,{}).get("number") or 0)
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    chk  = lambda k: p.get(k,{}).get("checkbox", False)
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    ttl  = lambda k: (p.get(k,{}).get("title") or [{}])[0].get("plain_text","")
    record = {
        "name": ttl("Name"), "account": sel("Account"), "date": date("Date"),
        "processed": num("Processed"), "accepted": num("Accepted"),
        "messaged": num("Messaged"), "replied": num("Replied"),
        "failed": num("Failed"), "is_baseline": chk("Is baseline")
    }
    key = (record["account"], record["date"])
    if key in existing_records:
        old = existing_records[key]
        if record["processed"] > 0 or record["is_baseline"]:
            existing_records[key] = record
        elif old.get("processed", 0) > 0:
            pass
        else:
            existing_records[key] = record
    else:
        existing_records[key] = record

# ── Replies ───────────────────────────────────────────────────────────────────
for page in query_db(replies_db):
    p = page["properties"]
    txt  = lambda k: ((p.get(k,{}).get("rich_text") or [{}])[0].get("plain_text","") if p.get(k,{}).get("rich_text") else (p.get(k,{}).get("title") or [{}])[0].get("plain_text","") if p.get(k,{}).get("title") else "")
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    url  = lambda k: (p.get(k,{}).get("url") or "")
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    reply = {
        "name": txt("Name"), "account": sel("Account"), "company": txt("Company"),
        "position": txt("Position"), "profile_url": url("Profile URL"),
        "their_reply": txt("Their reply"), "our_last_message": txt("Our last message"),
        "status": sel("Status"), "reply_date": date("Reply date"),
    }
    key = reply["profile_url"] or reply["name"]
    if key:
        existing_replies[key] = reply

# ── CRM ───────────────────────────────────────────────────────────────────────
crm_deals = []
for page in query_db(crm_db):
    p = page["properties"]
    txt  = lambda k: ((p.get(k,{}).get("rich_text") or [{}])[0].get("plain_text","") if p.get(k,{}).get("rich_text") else "")
    ttl  = lambda k: (p.get(k,{}).get("title") or [{}])[0].get("plain_text","")
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    num  = lambda k: (p.get(k,{}).get("number") or 0)
    url  = lambda k: (p.get(k,{}).get("url") or "")
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))

    stage = sel("Stage")
    if stage == "Lost":
        continue  # не показуємо Lost на дашборді

    crm_deals.append({
        "name":           ttl("Name"),
        "company":        txt("Company"),
        "contact":        txt("Contact"),
        "stage":          stage,
        "deal_size":      num("Deal size €"),
        "next_steps":     txt("Next steps"),
        "notes":          txt("Notes"),
        "linkedin_url":   url("LinkedIn URL"),
        "bitrix_url":    url("Bitrix URL"),
        "last_contact":   date("Last contact"),
        "next_steps_date": date("Next steps date"),
    })

# Сортуємо: спочатку за пріоритетом stage, потім за датою next steps
STAGE_ORDER = {"Negotiation": 0, "Proposal sent": 1, "Meeting scheduled": 2, "Contacted": 3, "Lead": 4, "Won": 5}
crm_deals.sort(key=lambda d: (STAGE_ORDER.get(d["stage"], 9), d["next_steps_date"] or "9999"))

# ── Збираємо фінальний data.json ──────────────────────────────────────────────
records = list(existing_records.values())
records.sort(key=lambda r: r.get("date") or "")

replies = list(existing_replies.values())
replies.sort(key=lambda r: r.get("reply_date") or "", reverse=True)

output = {
    "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "records": records,
    "replies": replies,
    "crm": crm_deals
}

# ── Daily aggregation ────────────────────────────────────────────────────────
daily = {}
for r in records:
    date = r.get("date")
    account = r.get("account")
    if not date or not account or r.get("is_baseline"):
        continue
    if date not in daily:
        daily[date] = {}
    daily[date][account] = {
        "processed": r.get("processed", 0),
        "accepted":  r.get("accepted",  0),
        "messaged":  r.get("messaged",  0),
        "replied":   r.get("replied",   0),
        "failed":    r.get("failed",    0),
    }

# Також додаємо baseline як першу точку якщо немає інших даних
baseline_records = [r for r in records if r.get("is_baseline")]
if baseline_records:
    base_date = baseline_records[0].get("date", "")
    if base_date and base_date not in daily:
        daily[base_date] = {}
        for r in baseline_records:
            acc = r.get("account")
            if acc:
                daily[base_date][acc] = {
                    "processed": r.get("processed", 0),
                    "accepted":  r.get("accepted",  0),
                    "messaged":  r.get("messaged",  0),
                    "replied":   r.get("replied",   0),
                    "failed":    r.get("failed",    0),
                }

output["daily"] = daily

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Records: {len(records)} | Replies: {len(replies)} | CRM deals: {len(crm_deals)}")
