import urllib.request, json, base64, time

pk = "pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
sk = "sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

# translate through nginx
body = json.dumps({"text": "every day at 9am"}).encode()
req = urllib.request.Request(
    "http://localhost:80/api/translate",
    data=body,
    headers={"Content-Type": "application/json"},
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
trace_id = result["trace_id"]
print("trace_id:", trace_id)

# submit feedback through nginx
fb = json.dumps(
    {"trace_id": trace_id, "rating": "positive", "comment": "test through nginx"}
).encode()
req2 = urllib.request.Request(
    "http://localhost:80/api/feedback",
    data=fb,
    headers={"Content-Type": "application/json"},
)
resp2 = urllib.request.urlopen(req2)
print("feedback status:", resp2.status)
print("feedback body:", resp2.read().decode())

# check Langfuse
time.sleep(1)
auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
req3 = urllib.request.Request(f"http://localhost:3000/api/public/traces/{trace_id}")
req3.add_header("Authorization", f"Basic {auth}")
trace = json.loads(urllib.request.urlopen(req3).read())
scores = trace.get("scores", [])
print("scores:", len(scores))
for s in scores:
    print(f"  {s['name']}: {s['value']} = {s.get('comment', '')}")
