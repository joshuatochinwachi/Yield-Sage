import os
import asyncio
import json
import httpx
import logging
import csv
from io import StringIO
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv

# Load env variables (automatically searches parent directories too)
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DUNE_QUERY_ID = "7595582"
DUNE_API_KEYS = [k.strip() for k in os.getenv("DUNE_API_KEYS", "").split(",") if k.strip()]

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

class DuneFetcher:
    def __init__(self):
        self.keys = DUNE_API_KEYS
        if not self.keys:
            raise ValueError("No DUNE_API_KEYS found in env.")
        self.current_key_idx = 0
        self.load_state()

    @property
    def current_key(self):
        return self.keys[self.current_key_idx]

    def load_state(self):
        state_file = os.path.join(os.path.dirname(__file__), "fetcher_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r") as f:
                    state = json.load(f)
                    self.current_key_idx = state.get("current_key_idx", 0) % len(self.keys)
                    logger.info(f"Loaded API key index {self.current_key_idx} from state file.")
            except Exception as e:
                logger.warning(f"Could not load state file: {e}")

    def save_state(self):
        state_file = os.path.join(os.path.dirname(__file__), "fetcher_state.json")
        try:
            with open(state_file, "w") as f:
                json.dump({"current_key_idx": self.current_key_idx}, f)
        except Exception as e:
            logger.warning(f"Could not save state file: {e}")

    def rotate_key(self):
        self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
        logger.info(f"Rotated key. New index: {self.current_key_idx}")
        self.save_state()

    async def check_key_credits(self, client: httpx.AsyncClient, api_key: str) -> bool:
        """Returns True if the key has available credits and is valid, False otherwise. Raises for network errors."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        headers = {"X-DUNE-API-KEY": api_key, "Content-Type": "application/json"}
        payload = {"start_date": today, "end_date": today}
        
        try:
            resp = await client.post("https://api.dune.com/api/v1/usage", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                periods = data.get("billing_periods", [])
                if not periods:
                    return True
                current_period = periods[0]
                used = current_period.get("credits_used", 0)
                included = current_period.get("credits_included", 0)
                logger.info(f"Key index {self.keys.index(api_key)} credit usage: {used}/{included}")
                return used < included
            elif resp.status_code in (401, 403):
                logger.warning(f"Key index {self.keys.index(api_key)} is invalid or unauthorized: {resp.status_code}")
                return False
            else:
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            # HTTPStatusError always has .response
            if e.response.status_code in (401, 403):
                return False
            raise
        except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
            # Transient network errors — propagate so the caller can retry
            logger.warning(f"Network error checking credits for key: {e}")
            raise

    async def select_valid_key(self, client: httpx.AsyncClient) -> str:
        """Loops through keys starting from current index to find one with credits. Raises on connection issues."""
        num_keys = len(self.keys)
        for i in range(num_keys):
            idx = (self.current_key_idx + i) % num_keys
            api_key = self.keys[idx]
            
            logger.info(f"Checking credits for key index {idx}...")
            try:
                has_credits = await self.check_key_credits(client, api_key)
                if has_credits:
                    if idx != self.current_key_idx:
                        logger.info(f"Switching active key index to {idx}")
                        self.current_key_idx = idx
                        self.save_state()
                    return api_key
                else:
                    logger.warning(f"Key index {idx} is exhausted. Moving to next key...")
            except httpx.HTTPStatusError as e:
                # HTTP status errors with response codes
                if e.response.status_code in (401, 403):
                    logger.warning(f"Key index {idx} is invalid ({e.response.status_code}). Moving to next key...")
                else:
                    raise
            except (httpx.ConnectError, httpx.TimeoutException, httpx.ReadError) as e:
                # Transient network errors — can't check credits, propagate to trigger retry
                logger.error(f"Network error while checking key index {idx}: {e}")
                raise
                    
        logger.error("All Dune API keys are exhausted or invalid!")
        return self.keys[self.current_key_idx]

    async def run(self):
        logger.info("Starting Dune fetch session...")
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Select key with credits
            api_key = await self.select_valid_key(client)
            
            headers = {"X-DUNE-API-KEY": api_key}
            max_retries = 30
            completed = False

            for attempt in range(1, max_retries + 1):
                # 2. Trigger query execution
                logger.info(f"Triggering Dune query execution (Attempt {attempt}/{max_retries})...")
                exec_url = f"https://api.dune.com/api/v1/query/{DUNE_QUERY_ID}/execute"
                
                exec_resp = await client.post(exec_url, headers=headers)
                if exec_resp.status_code != 200:
                    logger.error(f"Execution trigger failed: {exec_resp.text}")
                    if attempt < max_retries:
                        await asyncio.sleep(15)
                        continue
                    exec_resp.raise_for_status()
                    
                execution_id = exec_resp.json().get("execution_id")
                logger.info(f"Execution started: {execution_id}")
                
                # 3. Monitor execution status
                failed = False
                while not completed and not failed:
                    await asyncio.sleep(15)
                    status_url = f"https://api.dune.com/api/v1/execution/{execution_id}/status"
                    status_resp = await client.get(status_url, headers=headers)
                    
                    if status_resp.status_code != 200:
                        logger.warning(f"Status check failed: {status_resp.text}, retrying in 15s...")
                        continue
                        
                    state = status_resp.json().get("state")
                    logger.info(f"Execution status: {state}")
                    
                    if state == "QUERY_STATE_COMPLETED":
                        completed = True
                    elif state == "QUERY_STATE_FAILED":
                        logger.error(f"Query failed on Dune (Attempt {attempt}).")
                        failed = True
                
                if completed:
                    break
                    
                if failed and attempt < max_retries:
                    logger.info("Retrying execution after failure in 15 seconds...")
                    await asyncio.sleep(15)
                    continue
                elif failed:
                    raise RuntimeError("Dune query failed after maximum retries.")
            
            await asyncio.sleep(5)
            
            # 4. Fetch CSV results
            logger.info("Fetching CSV results...")
            res_url = f"https://api.dune.com/api/v1/query/{DUNE_QUERY_ID}/results/csv"
            res_resp = await client.get(res_url, headers=headers)
            if res_resp.status_code != 200:
                logger.error(f"Failed to fetch results: {res_resp.text}")
                res_resp.raise_for_status()
                
            csv_data = res_resp.text
            await self.ingest_data(csv_data)
            
            # 5. Rotate key after successful session for the next session
            logger.info("Dune fetch session completed successfully. Advancing key for next hour.")
            self.rotate_key()
            
    async def ingest_data(self, csv_text: str):
        logger.info("Parsing CSV and ingesting into Supabase...")
        
        # Use composite key: (protocol_name, pool_address) since multiple protocols share addresses
        resp = supabase.table("protocols").select("id, name, pool_address, image_url, app_link").execute()
        db_protocols_full = {
            (p["name"], p["pool_address"]): p 
            for p in resp.data 
            if p.get("pool_address")
        }
        db_protocols = {k: v["id"] for k, v in db_protocols_full.items()}
        
        reader = list(csv.DictReader(StringIO(csv_text)))
        new_protocols = []
        protocols_to_update = []
        seen_keys = set(db_protocols.keys())
        
        for row in reader:
            pool_address = row.get("Pool Address")
            protocol_name = row.get("Protocol", "Unknown")
            composite_key = (protocol_name, pool_address)
            
            image_val = row.get("Image") or None
            app_link_val = row.get("App Link") or None
            
            if pool_address:
                if composite_key not in seen_keys:
                    asset = row.get("Asset", "Unknown")
                    asset_lower = asset.lower()
                    risk = "stable" if any(x in asset_lower for x in ["usd", "dai"]) else "moderate"
                    
                    new_protocols.append({
                        "slug": f"{protocol_name}-{asset}-{pool_address[-6:]}".lower().replace(" ", "-").replace("/", "-"),
                        "name": protocol_name,
                        "pool_name": asset,
                        "pool_address": pool_address,
                        "risk_tag": risk,
                        "chain": "mantle",
                        "image_url": image_val,
                        "app_link": app_link_val
                    })
                    seen_keys.add(composite_key)
                else:
                    existing = db_protocols_full[composite_key]
                    needs_update = False
                    update_payload = {"id": existing["id"]}
                    
                    # Update if a non-null/empty image or app link is fetched but was null or different in the db
                    if image_val and existing.get("image_url") != image_val:
                        update_payload["image_url"] = image_val
                        needs_update = True
                    if app_link_val and existing.get("app_link") != app_link_val:
                        update_payload["app_link"] = app_link_val
                        needs_update = True
                        
                    if needs_update:
                        protocols_to_update.append(update_payload)
                        
        if new_protocols:
            logger.info(f"Auto-registering {len(new_protocols)} new protocols...")
            supabase.table("protocols").insert(new_protocols).execute()
            # Re-fetch database state
            resp = supabase.table("protocols").select("id, name, pool_address, image_url, app_link").execute()
            db_protocols_full = {
                (p["name"], p["pool_address"]): p 
                for p in resp.data 
                if p.get("pool_address")
            }
            db_protocols = {k: v["id"] for k, v in db_protocols_full.items()}
            
        if protocols_to_update:
            logger.info(f"Updating metadata for {len(protocols_to_update)} protocols...")
            for update in protocols_to_update:
                try:
                    supabase.table("protocols").update({
                        k: v for k, v in update.items() if k != "id"
                    }).eq("id", update["id"]).execute()
                except Exception as e:
                    logger.error(f"Error updating protocol {update['id']}: {e}")

        def safe_float(val):
            if val is None or str(val).strip() in ("", "<nil>"):
                return None
            return float(val)

        snapshots_to_insert = []
        for row in reader:
            pool_address = row.get("Pool Address")
            protocol_name = row.get("Protocol", "Unknown")
            composite_key = (protocol_name, pool_address)
            if composite_key in db_protocols and db_protocols[composite_key]:
                try:
                    snapshots_to_insert.append({
                        "protocol_id": db_protocols[composite_key],
                        "asset": row.get("Asset", "Unknown"),
                        "apy": safe_float(row.get("APY")),
                        "base_apy": safe_float(row.get("Base APY")),
                        "reward_apy": safe_float(row.get("Reward APY")),
                        "tvl_usd": safe_float(row.get("TVL ($)")),
                        "reward_tokens": row.get("Reward Tokens") or None,
                        "apy_1d": safe_float(row.get("APY (1D)")),
                        "apy_7d": safe_float(row.get("APY (7D)")),
                        "apy_30d": safe_float(row.get("APY (30D)")),
                        "raw_payload": row,
                        "fetched_at": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    logger.warning(f"Parse error for {pool_address}: {e}")
                    
        if snapshots_to_insert:
            supabase.table("yield_snapshots").insert(snapshots_to_insert).execute()
            logger.info(f"Inserted {len(snapshots_to_insert)} snapshots.")
        else:
            logger.info("No snapshots inserted.")
            
if __name__ == "__main__":
    fetcher = DuneFetcher()
    asyncio.run(fetcher.run())
