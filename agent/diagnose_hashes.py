import os
import json
import hashlib
from datetime import datetime
from supabase import create_client

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(url, key)

    # Fetch a few recommendations
    res = supabase.table("recommendations").select(
        "id, risk_tag, rank, apy_at_time, ai_reasoning, ai_model, on_chain_tx_hash, recommendation_hash, created_at, "
        "protocols(id, name, pool_name, pool_address)"
    ).order("created_at", desc=True).limit(20).execute()

    for rec in res.data:
        rec_hash = rec["recommendation_hash"]
        created_at_str = rec["created_at"].replace("Z", "+00:00")
        scored_at_dt = datetime.fromisoformat(created_at_str)
        
        # Get TVL
        snap_res = (
            supabase.table("yield_snapshots")
            .select("tvl_usd")
            .eq("protocol_id", rec["protocols"]["id"])
            .lte("fetched_at", rec["created_at"])
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        real_tvl = snap_res.data[0]["tvl_usd"] if snap_res.data else 0.0

        # Permutations to test
        configs = [
            # Standard current config
            {"version": "1.0", "source": "dune_query_7595582", "tvl": real_tvl, "addr_lower": True, "chain": True},
            # TVL = 0.00
            {"version": "1.0", "source": "dune_query_7595582", "tvl": 0.0, "addr_lower": True, "chain": True},
            # No chain/chain_id
            {"version": "1.0", "source": "dune_query_7595582", "tvl": real_tvl, "addr_lower": True, "chain": False},
            {"version": "1.0", "source": "dune_query_7595582", "tvl": 0.0, "addr_lower": True, "chain": False},
            # No version/source/chain
            {"version": None, "source": None, "tvl": real_tvl, "addr_lower": True, "chain": False},
            {"version": None, "source": None, "tvl": 0.0, "addr_lower": True, "chain": False},
            # No version/source/chain/tvl
            {"version": None, "source": None, "tvl": None, "addr_lower": True, "chain": False},
            # With original address casing
            {"version": "1.0", "source": "dune_query_7595582", "tvl": real_tvl, "addr_lower": False, "chain": True},
            {"version": "1.0", "source": "dune_query_7595582", "tvl": 0.0, "addr_lower": False, "chain": True},
        ]

        matched = False
        for cfg in configs:
            payload = {}
            if cfg["version"]:
                payload["version"] = cfg["version"]
            if cfg["source"]:
                payload["source"] = cfg["source"]
            
            payload["scored_at"] = scored_at_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            payload["risk_tag"] = rec["risk_tag"]
            payload["rank"] = rec["rank"]
            payload["protocol_name"] = rec["protocols"]["name"]
            payload["pool_name"] = rec["protocols"]["pool_name"]
            
            addr = rec["protocols"]["pool_address"]
            payload["pool_address"] = addr.lower() if (cfg["addr_lower"] and addr) else addr
            
            payload["apy_at_time"] = f"{float(rec['apy_at_time']):.4f}"
            
            if cfg["tvl"] is not None:
                payload["tvl_usd"] = f"{float(cfg['tvl']):.2f}"
            
            payload["ai_reasoning"] = rec["ai_reasoning"].strip()
            payload["ai_model"] = rec["ai_model"]
            
            if cfg["chain"]:
                payload["chain"] = "solana"
                payload["chain_id"] = 5000

            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            computed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            if computed == rec_hash:
                print(f"Match found for {rec['id']} (Created: {rec['created_at']}): {cfg}")
                matched = True
                break
        
        if not matched:
            print(f"❌ NO MATCH for {rec['id']} (Created: {rec['created_at']})")
            # Dump the DB record details to inspect it
            print("DB Hash:", rec_hash)
            print("Payload properties:")
            print("  protocol:", rec["protocols"]["name"])
            print("  pool:", rec["protocols"]["pool_name"])
            print("  address:", rec["protocols"]["pool_address"])
            print("  apy:", rec["apy_at_time"])
            print("  ai_reasoning:", repr(rec["ai_reasoning"]))
            print("  ai_model:", rec["ai_model"])
            print("---")

if __name__ == "__main__":
    main()
