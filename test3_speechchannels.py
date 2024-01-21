import json
import requests
headers = {"Authorization": f"Bearer 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"}
API_URL = "https://api-inference.huggingface.co/models/speechbrain/sepformer-wsj02mix"
def query(filename):
    with open(filename, "rb") as f:
        data = f.read()
    response = requests.request("POST", API_URL, headers=headers, data=data)
    return json.loads(response.content.decode("utf-8"))
data = query(r"Data\recording_06012024233332.m4a")
print(data)