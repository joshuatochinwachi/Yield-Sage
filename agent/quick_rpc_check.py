# quick_rpc_check.py — run once to verify wallet + RPC are working
import os
from solana.rpc.api import Client
from solders.keypair import Keypair
from dotenv import load_dotenv

load_dotenv()

rpc_url = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
client = Client(rpc_url)
print("Connected:", client.is_connected())
print("Cluster:", rpc_url)

priv_key = os.environ.get("SOLANA_PRIVATE_KEY")
if priv_key:
    try:
        keypair = Keypair.from_base58_string(priv_key)
        balance_resp = client.get_balance(keypair.pubkey())
        balance_sol = balance_resp.value / 10**9
        print("Wallet:", keypair.pubkey())
        print("Balance (SOL):", balance_sol)
    except Exception as e:
        print("Error reading keypair:", e)
else:
    print("SOLANA_PRIVATE_KEY not set in environment.")
