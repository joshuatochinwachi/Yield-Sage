import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load from .env
from dotenv import find_dotenv
load_dotenv(find_dotenv())

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

def seed_protocols():
    protocols = [
        {
            "slug": "agni-usdt-usdt0",
            "name": "Agni Finance",
            "pool_name": "USDT-USDT0",
            "pool_address": "https://mantlescan.xyz/address/0x0d290c8e7f3ffa5267de4b1f9f6f6d8d578624ac",
            "risk_tag": "stable",
            "chain": "mantle",
            "is_active": True
        },
        {
            "slug": "agni-usde-wmnt",
            "name": "Agni Finance",
            "pool_name": "USDe-WMNT",
            "pool_address": "https://mantlescan.xyz/address/0xeafc4d6d4c3391cd4fc10c85d2f5f972d58c0dd5",
            "risk_tag": "moderate",
            "chain": "mantle",
            "is_active": True
        },
        {
            "slug": "agni-susde-usde",
            "name": "Agni Finance",
            "pool_name": "sUSDe-USDe",
            "pool_address": "https://mantlescan.xyz/address/0x07277f7c1567b5324aa50a3d2f1f003e2287fbfc",
            "risk_tag": "aggressive",
            "chain": "mantle",
            "is_active": True
        },
        {
            "slug": "agni-weth-cmeth",
            "name": "Agni Finance",
            "pool_name": "WETH-cmETH",
            "pool_address": "https://mantlescan.xyz/address/0x0d9e39d357337edde4a9bc12178da40256e2f533",
            "risk_tag": "stable",
            "chain": "mantle",
            "is_active": True
        }
    ]
    
    for p in protocols:
        try:
            supabase.table('protocols').insert(p).execute()
            print(f"Inserted protocol: {p['slug']}")
        except Exception as e:
            print(f"Failed to insert {p['slug']} or already exists: {e}")

if __name__ == "__main__":
    print("Seeding database...")
    seed_protocols()
    print("Done.")
