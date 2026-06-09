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

# ── Outreach stats ────────────────────────────────────────────────────────────
records = []
for page in query_db(outreach_db):
    p = page["properties"]
    num  = lambda k: (p.get(k,{}).get("number") or 0)
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    chk  = lambda k: p.get(k,{}).get("checkbox", False)
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    ttl  = lambda k: (p.get(k,{}).get("title") or [{}])[0].get("plain_text","")
    records.append({
        "name": ttl("Name"), "account": sel("Account"), "date": date("Date"),
        "processed": num("Processed"), "accepted": num("Accepted"),
        "messaged": num("Messaged"), "replied": num("Replied"),
        "failed": num("Failed"), "is_baseline": chk("Is baseline")
    })
records.sort(key=lambda r: r["date"] or "")

# ── Replies ───────────────────────────────────────────────────────────────────
replies = []
for page in query_db(replies_db):
    p = page["properties"]
    txt  = lambda k: ((p.get(k,{}).get("rich_text") or [{}])[0].get("plain_text","") if p.get(k,{}).get("rich_text") else (p.get(k,{}).get("title") or [{}])[0].get("plain_text","") if p.get(k,{}).get("title") else "")
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    url  = lambda k: (p.get(k,{}).get("url") or "")
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    replies.append({
        "name":        txt("Name"),
        "account":     sel("Account"),
        "company":     txt("Company"),
        "position":    txt("Position"),
        "profile_url": url("Profile URL"),
        "their_reply": txt("Their reply"),
        "status":      sel("Status"),
        "reply_date":  date("Reply date"),
    })
replies.sort(key=lambda r: r["reply_date"] or "", reverse=True)

with open("data.json", "w", encoding="utf-8") as f:
    json.dump({
        "updated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "records": records,
        "replies": replies
    }, f, ensure_ascii=False, indent=2)

print(f"Written {len(records)} outreach records, {len(replies)} replies")
