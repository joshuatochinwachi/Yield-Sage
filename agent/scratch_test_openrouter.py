import os
import asyncio
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

async def test():
    key = os.getenv("OPENROUTER_API_KEY")
    client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    for model in ["nvidia/nemotron-3-super-120b-a12b:free", "liquid/lfm-2.5-2.6b:free"]:
        print(f"\n--- Testing {model} ---")
        try:
            res = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are YieldSage. Be concise."},
                    {"role": "user", "content": "Give me 2 bullet points on Solana staking APY."}
                ],
                max_tokens=500,
                temperature=0.2,
            )
            choice = res.choices[0]
            print("Finish Reason:", choice.finish_reason)
            print("Content:", repr(choice.message.content))
            print("Model dump:", choice.message.model_dump())
        except Exception as e:
            print("Error:", e)

    # Check telegram_messages columns in Supabase
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if url and key:
        sb = create_client(url, key)
        r = sb.table("telegram_messages").select("*").limit(1).execute()
        if r.data:
            print("\ntelegram_messages columns:", list(r.data[0].keys()))
        else:
            print("\ntelegram_messages is empty")

if __name__ == "__main__":
    asyncio.run(test())
