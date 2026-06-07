# quick_rpc_check.py — run once to verify wallet + RPC are working
import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

w3 = Web3(Web3.HTTPProvider(os.environ.get("MANTLE_RPC_URL", "https://rpc.mantle.xyz")))
print("Connected:", w3.is_connected())
print("Chain ID:", w3.eth.chain_id)   # Should print 5000

priv_key = os.environ.get("YIELDSAGE_WALLET_PRIVATE_KEY")
if priv_key:
    account = w3.eth.account.from_key(priv_key)
    balance = w3.eth.get_balance(account.address)
    print("Wallet:", account.address)
    print("Balance (MNT):", w3.from_wei(balance, "ether"))
else:
    print("YIELDSAGE_WALLET_PRIVATE_KEY not set in environment.")
