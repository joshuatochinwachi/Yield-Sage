import os
import sys
import json
import hashlib
from datetime import datetime

# Add agent path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "agent")))
from fetcher import supabase
from logger import build_recommendation_payload

tx = "3K5Yj9CnLmXP6cqm8PhdUXJF4YmnsH7GZeS6EER5SrZnPXnDDBXbTz9g5yoK8agytZcwjPR9qWMyCT3N7fWyNNtb"

print(f"Querying recommendation for TX: {tx}")
res = supabase.table("recommendations").select(
    "*, protocols(*)"
).eq("on_chain_tx_hash", tx).execute()

if not res.data:
    print("No record found!")
    sys.exit(1)

rec = res.data[0]
print("DB RECORD:")
print(json.dumps(rec, indent=2, default=str))

target_hash = rec["recommendation_hash"]
print(f"\nTarget stored hash: {target_hash}")

# Check created_at
created_at_str = rec["created_at"].replace("Z", "+00:00")
scored_at_dt = datetime.fromisoformat(created_at_str)

# Build payload using build_recommendation_payload
p_name = rec["protocols"]["name"] if rec.get("protocols") else "Unknown"
pool_name = rec["protocols"]["pool_name"] if rec.get("protocols") else "Unknown"
pool_addr = (rec["protocols"]["pool_address"] if rec.get("protocols") else "") or ""
tvl = float(rec.get("tvl_usd") or 0.0)

payload = build_recommendation_payload(
    protocol_name=p_name,
    pool_name=pool_name,
    pool_address=pool_addr,
    risk_tag=rec["risk_tag"],
    rank=rec["rank"],
    apy_at_time=rec["apy_at_time"],
    tvl_usd=tvl,
    ai_reasoning=rec["ai_reasoning"],
    ai_model=rec["ai_model"],
    scored_at=scored_at_dt,
)

canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
computed_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

print("\nComputed Payload:")
print(canonical_json)
print(f"\nComputed Hash: {computed_hash}")
print(f"Match? {computed_hash == target_hash}")
