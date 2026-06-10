import urllib.request,json,os
from datetime import datetime,timezone

APOLLO_KEY=os.environ["APOLLO_KEY"]

def apollo(path,body=None,method="POST"):
    req=urllib.request.Request(f"https://api.apollo.io/v1/{path}",
        data=json.dumps(body or {}).encode(),
        headers={"Content-Type":"application/json","Cache-Control":"no-cache","X-Api-Key":APOLLO_KEY},
        method=method)
    with urllib.request.urlopen(req) as r:return json.loads(r.read())

data=apollo("emailer_campaigns/search",{"per_page":100})
seqs=[]
for c in data.get("emailer_campaigns",[]):
    sid=c.get("id")
    try:
        s=apollo(f"emailer_campaigns/{sid}",{},method="GET").get("emailer_campaign",c)
    except:s=c
    cs=s.get("contact_statuses") or {}
    sent=s.get("unique_delivered",0)
    rr=s.get("reply_rate",0)
    replied=round(sent*rr) if sent>0 else 0
    seqs.append({"id":sid,"name":s.get("name",""),"active":s.get("active",False),"stats":{"num_active":cs.get("active",0),"num_paused":cs.get("paused",0),"num_finished":cs.get("finished",0),"num_bounced":cs.get("bounced",0),"num_not_sent":cs.get("not_sent",0),"unique_scheduled":s.get("unique_scheduled",0),"emails_sent":sent,"emails_opened":s.get("unique_opened",0),"emails_clicked":s.get("unique_clicked",0),"emails_replied":replied,"open_rate":round(s.get("open_rate",0)*100,1),"reply_rate":round(rr*100,1)}})
    print(f"  {s.get('name')} | active={cs.get('active',0)} sent={sent} replied={replied} | reply={round(rr*100,1)}%")

with open("apollo.json","w",encoding="utf-8") as f:
    json.dump({"updated_at":datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),"sequences":seqs},f,ensure_ascii=False,indent=2)
print(f"Written {len(seqs)} sequences")
