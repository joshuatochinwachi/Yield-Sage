"""Quick check: verify that migrations 004 and 005 have been applied."""
import os
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())

from supabase import create_client

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
s = create_client(url, key)

tables_to_check = ["chat_memory", "paper_trades", "telegram_messages"]

for table in tables_to_check:
    try:
        r = s.table(table).select("id").limit(1).execute()
        print(f"  [OK] {table} exists (rows: {len(r.data)})")
    except Exception as e:
        print(f"  [MISSING] {table}: {e}")

# Check telegram_messages accepts 'pending' status
try:
    # Just test a select with status filter
    r = s.table("telegram_messages").select("id").eq("status", "pending").limit(1).execute()
    print(f"  [OK] telegram_messages accepts 'pending' status filter")
except Exception as e:
    print(f"  [ISSUE] telegram_messages pending status: {e}")

print("\nDone.")
