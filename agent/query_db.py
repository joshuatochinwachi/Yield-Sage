import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
supabase = create_client(url, key)

res = supabase.table("protocols").select("*").eq("is_active", True).execute()
print(f"Active rows in protocols table: {len(res.data)}")
unique_names = sorted(list(set(r["name"] for r in res.data if r.get("name"))))
print(f"Unique protocol names: {len(unique_names)}")
print(unique_names)

print("\nDetail of rows in protocols table:")
for r in res.data:
    print(f"ID: {r['id']}, Slug: {r['slug']}, Name: {r['name']}, Pool Name: {r['pool_name']}, IsActive: {r['is_active']}")

# Also query the yields snapshots to see which protocol IDs actually have snapshots
snap_res = supabase.table("yield_snapshots").select("protocol_id, fetched_at").execute()
snaps = snap_res.data
snap_pids = set(s["protocol_id"] for s in snaps)
print(f"\nTotal yield snapshots: {len(snaps)}")
print(f"Protocol IDs with snapshots: {len(snap_pids)}")

# Find out what protocol names have snapshots
names_with_snaps = set()
for r in res.data:
    if r["id"] in snap_pids:
        names_with_snaps.add(r["name"])
print(f"Unique protocols with snapshots: {len(names_with_snaps)}")
print(sorted(list(names_with_snaps)))
