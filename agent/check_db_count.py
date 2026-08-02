import os
import sys
from supabase import create_client
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing in .env")
    sys.exit(1)

db = create_client(url, key)

proto_res = db.table("protocols").select("id", count="exact").execute()
proto_active = db.table("protocols").select("id", count="exact").eq("is_active", True).execute()
snap_res = db.table("yield_snapshots").select("id", count="exact").execute()
snap_default = db.table("yield_snapshots").select("id").execute()

page1 = db.table("yield_snapshots").select("id").range(0, 999).execute()
page2 = db.table("yield_snapshots").select("id").range(1000, 1999).execute()
page3 = db.table("yield_snapshots").select("id").range(2000, 2999).execute()

print(f"Total protocols in DB: {proto_res.count}")
print(f"Active protocols in DB: {proto_active.count}")
print(f"Total yield snapshots in DB: {snap_res.count}")
print(f"Default .select('id') returned rows: {len(snap_default.data or [])}")
print(f"Page 1 range(0, 999) returned: {len(page1.data or [])}")
print(f"Page 2 range(1000, 1999) returned: {len(page2.data or [])}")
print(f"Page 3 range(2000, 2999) returned: {len(page3.data or [])}")
