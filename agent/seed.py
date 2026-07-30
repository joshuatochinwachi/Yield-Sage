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
            "slug": "kamino-usdc",
            "name": "Kamino Finance",
            "pool_name": "USDC",
            "pool_address": "https://solscan.io/account/ByYiZxp8QrdN9qbdtaAiePN8AAr3qvTPppNJDpf5DVJ5",
            "risk_tag": "stable",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "marginfi-usdc",
            "name": "MarginFi",
            "pool_name": "USDC",
            "pool_address": "https://solscan.io/account/2s37akK2eyBbp8DZgCm7RtsaEz8eJP3Nxd4urLHQv7yB",
            "risk_tag": "stable",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "jito-sol",
            "name": "Jito",
            "pool_name": "JitoSOL",
            "pool_address": "https://solscan.io/account/J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
            "risk_tag": "moderate",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "marinade-msol",
            "name": "Marinade Finance",
            "pool_name": "mSOL",
            "pool_address": "https://solscan.io/account/mSoLzYCxHdYgdzU16g5QSh3i5K3z3KZK7ytfqcJm7So",
            "risk_tag": "moderate",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "orca-sol-usdc",
            "name": "Orca",
            "pool_name": "SOL-USDC",
            "pool_address": "https://solscan.io/account/HJPjoWUrhoZzkNfRpHuieeFk9WcZWjwy6PBjZ81ngndJ",
            "risk_tag": "aggressive",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "raydium-sol-usdc",
            "name": "Raydium",
            "pool_name": "SOL-USDC",
            "pool_address": "https://solscan.io/account/58oQChx4yWmvKec8raoFH2oYy3r8nRRXqC4cSqMpqLmt",
            "risk_tag": "aggressive",
            "chain": "solana",
            "is_active": True
        },
        {
            "slug": "drift-usdc",
            "name": "Drift Protocol",
            "pool_name": "USDC",
            "pool_address": "https://solscan.io/account/JCNCMFXo5M5qwUPg2Utu1u6YWp3MbygxqBsBeXXJfrw",
            "risk_tag": "stable",
            "chain": "solana",
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
