import os
import json
from supabase import create_client

def main():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    supabase = create_client(url, key)
    res = supabase.table("recommendations").select("id, on_chain_tx_hash, recommendation_hash, created_at").not_.is_("on_chain_tx_hash", "null").limit(5).execute()
    print("Found entries:")
    print(json.dumps(res.data, indent=2))

    # Also search for the specific hash the user reported: 0x1af457148117e2b1d866af5c086a53ba9a63764f96f8983b75cb0f96b77adbfa
    target = "0x1af457148117e2b1d866af5c086a53ba9a63764f96f8983b75cb0f96b77adbfa"
    print(f"\nSearching for target: {target}")
    res2 = supabase.table("recommendations").select("id, on_chain_tx_hash").eq("on_chain_tx_hash", target).execute()
    print("Target direct search results:", res2.data)
    
    # Try searching case-insensitively or with different prefixes/suffixes if not found
    res3 = supabase.table("recommendations").select("id, on_chain_tx_hash").ilike("on_chain_tx_hash", f"%{target.lower().replace('0x', '')}%").execute()
    print("Target partial/case-insensitive search results:", res3.data)

if __name__ == "__main__":
    main()
