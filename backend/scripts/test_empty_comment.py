import urllib.request, json, base64, time

pk = "pk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
sk = "sk-lf-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

def test_feedback(comment):
    body = json.dumps({"text": "every day at 9am"}).encode()
    req = urllib.request.Request("http://localhost:8000/api/translate", data=body, headers={"Content-Type":"application/json"})
    tid = json.loads(urllib.request.urlopen(req).read())["trace_id"]
    print(f"trace_id: {tid}")

    fb = json.dumps({"trace_id": tid, "rating": "positive", "comment": comment}).encode()
    req2 = urllib.request.Request("http://localhost:8000/api/feedback", data=fb, headers={"Content-Type":"application/json"})
    resp2 = urllib.request.urlopen(req2)
    print(f"  feedback status: {resp2.status}")

    time.sleep(2)
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    req3 = urllib.request.Request(f"http://localhost:3000/api/public/traces/{tid}")
    req3.add_header("Authorization", f"Basic {auth}")
    trace = json.loads(urllib.request.urlopen(req3).read())
    scores = trace.get("scores", [])
    print(f"  scores: {len(scores)}")
    for s in scores:
        print(f"    {s['name']} = {s['value']} comment={s.get('comment','')}")

print("Test 1: empty comment")
test_feedback("")
print("\nTest 2: with comment")
test_feedback("works great")
