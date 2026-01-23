import json
import urllib.request

url = 'http://localhost:8000/chat'
payload = {
    "message": "Hello",
    "conversation_history": []
}

data = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=30)
    print(resp.read().decode('utf-8'))
except Exception as e:
    print('chat request failed:', e)
