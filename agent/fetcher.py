import os
import sys
import asyncio
import logging
from datetime import datetime, timezone
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv

# Load env variables (automatically searches parent directories too)
load_dotenv(find_dotenv())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(url, key)

# Import the live Solana fetch logic
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from solana_pools_live import build_enriched_view
except ImportError:
    from solana_pools_live import build_enriched_view

class SolanaFetcher:
    def __init__(self, max_retries: int = 3, retry_delay: float = 5.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def log_error(self, job_type: str, error_msg: str, stack_trace: str = None):
        """Logs job failures to Supabase agent_errors table for admin diagnostics."""
        try:
            supabase.table("agent_errors").insert({
                "job_type": job_type,
                "error_message": str(error_msg),
                "stack_trace": str(stack_trace) if stack_trace else None,
                "created_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Failed to log error to agent_errors table: {e}")

    async def run(self):
        logger.info("Starting Solana pools live fetch session...")
        loop = asyncio.get_event_loop()
        enriched_df = None

        # 1. Retry fetch with exponential backoff
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Fetching live Solana pool data (Attempt {attempt}/{self.max_retries})...")
                enriched_df = await loop.run_in_executor(None, build_enriched_view)
                if enriched_df is not None and not enriched_df.empty:
                    logger.info(f"Successfully fetched {len(enriched_df)} Solana pools.")
                    break
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{self.max_retries} failed during fetch: {e}")
                if attempt < self.max_retries:
                    wait_time = self.retry_delay * (2 ** (attempt - 1))
                    logger.info(f"Retrying fetch in {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                else:
                    err_msg = f"All {self.max_retries} attempts failed to fetch live Solana yield data: {e}"
                    logger.error(err_msg)
                    await self.log_error("fetch", err_msg)
                    raise e

        if enriched_df is not None and not enriched_df.empty:
            await self.ingest_data(enriched_df)

    async def ingest_data(self, df: pd.DataFrame):
        logger.info("Parsing enriched dataframe and ingesting into Supabase...")

        try:
            # 1. Fetch existing protocols from Supabase safely
            try:
                resp = supabase.table("protocols").select("id, name, pool_name, pool_address, image_url, app_link").execute()
            except Exception:
                resp = supabase.table("protocols").select("id, name, pool_name, pool_address, image_url, app_link").execute()




        except Exception as e:
            err_msg = f"Failed to query existing protocols from Supabase: {e}"
            logger.error(err_msg)
            await self.log_error("fetch", err_msg)
            raise e



        
        def get_address(p):
            return p.get("program_address") or p.get("pool_address")

        db_protocols_full = {
            (p["name"].lower(), (get_address(p) or "").lower(), p["pool_name"].lower()): p
            for p in resp.data
        }
        
        db_protocols_by_pair = {
            (p["name"].lower(), p["pool_name"].lower(), (p.get("pool_address") or "").lower()): p["id"]
            for p in resp.data
        }
        # Fallback map by name + pool_name for backward compatibility
        db_protocols_fallback = {
            (p["name"].lower(), p["pool_name"].lower()): p["id"]
            for p in resp.data
        }
        
        db_protocols_ids = {k: v["id"] for k, v in db_protocols_full.items()}

        new_protocols = []
        protocols_to_update = []
        seen_keys = set()
        seen_pairs = set(db_protocols_by_pair.keys())

        records = df.to_dict(orient="records")

        for row in records:
            protocol_name = str(row.get("Protocol") or "Unknown").strip()
            asset = str(row.get("Asset") or "Unknown").strip()
            raw_address = str(row.get("Pool Address") or "").strip() or None
            pool_id = str(row.get("Pool ID") or "").strip()
            
            # Format non-null pool addresses with solscan URL
            if raw_address:
                if raw_address.startswith("http://") or raw_address.startswith("https://"):
                    pool_address = raw_address
                else:
                    pool_address = f"https://solscan.io/account/{raw_address}"
            else:
                pool_address = None
            
            image_val = row.get("Image") or None
            app_link_val = row.get("App Link") or None

            composite_key = (protocol_name.lower(), (pool_address or "").lower(), asset.lower())
            # Use pool_id or pool_address so multiple pools for the same asset pair are tracked separately
            unique_pool_ref = pool_id if pool_id else (raw_address or "")
            pair_key = (protocol_name.lower(), asset.lower(), unique_pool_ref.lower())
            fallback_key = (protocol_name.lower(), asset.lower())

            asset_lower = asset.lower()
            risk = "stable" if any(x in asset_lower for x in ["usd", "usdc", "usdt", "dai", "pyusd"]) else "moderate"

            if pair_key not in seen_pairs:
                id_slug_part = f"-{unique_pool_ref[:8]}" if unique_pool_ref else ""
                slug = f"{protocol_name}-{asset}{id_slug_part}".lower().replace(" ", "-").replace("/", "-")
                
                new_protocol_record = {
                    "slug": slug,
                    "name": protocol_name,
                    "pool_name": asset,
                    "risk_tag": risk,
                    "chain": "solana",
                    "image_url": image_val,
                    "app_link": app_link_val,
                    "pool_address": pool_address
                }

                new_protocols.append(new_protocol_record)
                seen_keys.add(composite_key)
                seen_pairs.add(pair_key)
            else:
                existing_id = db_protocols_by_pair.get(pair_key) or db_protocols_fallback.get(fallback_key)
                if existing_id:
                    existing = next((p for p in resp.data if p["id"] == existing_id), None)
                    if existing:
                        needs_update = False
                        update_payload = {"id": existing["id"]}

                        if image_val and existing.get("image_url") != image_val:
                            update_payload["image_url"] = image_val
                            needs_update = True
                        if app_link_val and existing.get("app_link") != app_link_val:
                            update_payload["app_link"] = app_link_val
                            needs_update = True
                        if pool_address and not get_address(existing):
                            update_payload["pool_address"] = pool_address
                            needs_update = True

                        if needs_update:
                            protocols_to_update.append(update_payload)


        # Insert new protocols
        if new_protocols:
            logger.info(f"Auto-registering {len(new_protocols)} new Solana protocols...")
            try:
                supabase.table("protocols").insert(new_protocols).execute()
            except Exception as e:
                logger.error(f"Error registering new protocols: {e}")
                await self.log_error("fetch", f"Error inserting protocols: {e}")

            # Re-fetch database state
            try:
                try:
                    resp = supabase.table("protocols").select("id, name, pool_name, pool_address, image_url, app_link").execute()
                except Exception:
                    resp = supabase.table("protocols").select("id, name, pool_name, pool_address, image_url, app_link").execute()

                db_protocols_by_pair = {
                    (p["name"].lower(), p["pool_name"].lower()): p["id"]
                    for p in resp.data
                }
            except Exception as e:
                logger.error(f"Error re-fetching protocols: {e}")


        # Perform updates
        if protocols_to_update:
            logger.info(f"Updating metadata for {len(protocols_to_update)} protocols...")
            for update in protocols_to_update:
                try:
                    update_dict = {k: v for k, v in update.items() if k != "id"}
                    supabase.table("protocols").update(update_dict).eq("id", update["id"]).execute()
                except Exception as e:
                    logger.error(f"Error updating protocol {update['id']}: {e}")

        # Insert Snapshots
        def safe_float(val):
            if val is None or pd.isna(val) or str(val).strip() in ("", "<nil>", "nan"):
                return None
            try:
                return float(val)
            except (ValueError, TypeError):
                return None

        snapshots_to_insert = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for row in records:
            protocol_name = str(row.get("Protocol") or "Unknown").strip()
            asset = str(row.get("Asset") or "Unknown").strip()
            raw_address = str(row.get("Pool Address") or "").strip() or None
            pool_id = str(row.get("Pool ID") or "").strip()
            unique_pool_ref = pool_id if pool_id else (raw_address or "")

            pair_key = (protocol_name.lower(), asset.lower(), unique_pool_ref.lower())
            fallback_key = (protocol_name.lower(), asset.lower())

            protocol_id = db_protocols_by_pair.get(pair_key) or db_protocols_fallback.get(fallback_key)
            if protocol_id:
                try:
                    snapshots_to_insert.append({
                        "protocol_id": protocol_id,
                        "asset": asset,
                        "apy": safe_float(row.get("APY")),
                        "base_apy": safe_float(row.get("Base APY")),
                        "reward_apy": safe_float(row.get("Reward APY")),
                        "tvl_usd": safe_float(row.get("TVL ($)")),
                        "reward_tokens": row.get("Reward Tokens") or None,
                        "apy_1d": safe_float(row.get("APY (1D)")),
                        "apy_7d": safe_float(row.get("APY (7D)")),
                        "apy_30d": safe_float(row.get("APY (30D)")),
                        "raw_payload": {k: (None if pd.isna(v) else v) for k, v in row.items()},
                        "fetched_at": now_iso
                    })
                except Exception as e:
                    logger.warning(f"Parse error for snapshot {protocol_name} - {asset}: {e}")

        if snapshots_to_insert:
            batch_size = 100
            success_count = 0
            for i in range(0, len(snapshots_to_insert), batch_size):
                batch = snapshots_to_insert[i:i + batch_size]
                try:
                    supabase.table("yield_snapshots").insert(batch).execute()
                    success_count += len(batch)
                except Exception as e:
                    err_msg = f"Batch snapshot insert failed (items {i} to {i+len(batch)}): {e}"
                    logger.error(err_msg)
                    await self.log_error("fetch", err_msg)
            logger.info(f"Successfully inserted {success_count}/{len(snapshots_to_insert)} Solana yield snapshots.")
        else:
            logger.info("No yield snapshots to insert.")

# SolanaFetcher is the live implementation. Legacy alias kept for scheduler backward compatibility.
DuneFetcher = SolanaFetcher

if __name__ == "__main__":
    fetcher = SolanaFetcher()
    asyncio.run(fetcher.run())

