import requests

API_KEY = " Insert API KEY here "
NAMESPACE = "mantle"
TABLE_NAME = "dataset_protocol_apy"

response = requests.delete(
    f"https://api.dune.com/api/v1/uploads/{NAMESPACE}/{TABLE_NAME}",
    headers={"X-DUNE-API-KEY": API_KEY}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")