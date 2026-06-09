import urllib.request, json, os
from datetime import datetime

token = os.environ["NOTION_TOKEN"]
db_id = os.environ["NOTION_DATABASE_ID"]
url = "https://api.notion.com/v1/databases/" + db_id + "/query"
headers = {"Authorization": "Bearer " + token, "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
req = urllib.request.Request(url, data=b"{}", headers=headers, method="POST")
with urllib.request.urlopen(req) as r:
    raw = json.loads(r.read())

records = []
for page in raw.get("results", []):
    p = page["properties"]
    num  = lambda k: (p.get(k,{}).get("number") or 0)
    sel  = lambda k: ((p.get(k,{}).get("select") or {}).get("name",""))
    chk  = lambda k: p.get(k,{}).get("checkbox", False)
    date = lambda k: ((p.get(k,{}).get("date") or {}).get("start"))
    ttl  = lambda k: (p.get(k,{}).get("title") or [{}])[0].get("plain_text","")
    records.append({"name":ttl("Name"),"account":sel("Account"),"date":date("Date"),"processed":num("Processed"),"accepted":num("Accepted"),"messaged":num("Messaged"),"replied":num("Replied"),"failed":num("Failed"),"is_baseline":chk("Is baseline")})

records.sort(key=lambda r: r["date"] or "")
with open("data.json","w",encoding="utf-8") as f:
    json.dump({"updated_at":datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),"records":records},f,ensure_ascii=False,indent=2)
print("Written", len(records), "records")
