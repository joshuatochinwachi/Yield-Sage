"""
Free-only model finder.
- OpenRouter: filters by pricing == 0 (the API tells us).
- Others: lists models, then sends a 1-token probe to a capped shortlist.
  Status meaning:
    200 = callable on your key right now
    429 = exists, rate limited (likely free but quota-bound)
    402 = payment required (NOT free for you)
    401 = bad key | 403/404 = no access / wrong id
Usage:
    python agent\\free_models.py             # list only, no quota used
    python agent\\free_models.py --probe     # also probe (spends ~1 request per model)
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

load_dotenv()

PROBE = "--probe" in sys.argv
MAX_PROBES_PER_PROVIDER = 12
MIN_CTX_OPENROUTER = 16000

PROVIDERS = {
    "Groq": ("GROQ_API_KEY", "https://api.groq.com/openai/v1"),
    "SambaNova": ("SAMBANOVA_API_KEY", "https://api.sambanova.ai/v1"),
    "Cerebras": ("CEREBRAS_API_KEY", "https://api.cerebras.ai/v1"),
    "NVIDIA": ("NVIDIA_API_KEY", "https://integrate.api.nvidia.com/v1"),
    "Gemini": ("GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta/openai"),
    "OpenRouter": ("OPENROUTER_API_KEY", "https://openrouter.ai/api/v1"),
}

SKIP_WORDS = (
    "whisper", "tts", "guard", "embed", "orpheus", "transcribe", "moderation",
    "imagen", "veo", "lyria", "aqa", "safety", "rerank", "retriever", "parse",
    "clip", "vision-only", "image", "audio", "-vl", "reasoning",
)

# Only probe models that look like general chat models, so we do not burn quota
PROBE_KEYWORDS = (
    "llama", "qwen", "gemma", "gpt-oss", "deepseek", "mistral", "nemotron",
    "gemini", "glm", "kimi", "minimax", "inkling",
)


def is_free(m):
    p = m.get("pricing") or {}
    try:
        return float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0
    except (TypeError, ValueError):
        return False


def fetch_models(base, key):
    r = requests.get(f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}: {r.text[:160]}"
    return r.json().get("data", []), None


def probe(base, key, model_id):
    try:
        r = requests.post(
            f"{base}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": model_id,
                "messages": [{"role": "user", "content": "Say OK"}],
                "max_tokens": 1,
                "temperature": 0,
            },
            timeout=45,
        )
        return r.status_code
    except requests.RequestException:
        return "ERR"


def run(name, env_key, base):
    print(f"\n=== {name} ===")
    key = os.getenv(env_key)
    if not key:
        print(f"SKIPPED: {env_key} not set")
        return

    models, err = fetch_models(base, key)
    if err:
        print(err)
        return

    candidates = []
    for m in sorted(models, key=lambda x: x.get("id", "")):
        mid = m.get("id", "")
        if name == "Gemini" and mid.startswith("models/"):
            mid = mid[len("models/"):]
        low = mid.lower()
        if any(w in low for w in SKIP_WORDS):
            continue
        ctx = m.get("context_window") or m.get("context_length") or "?"

        if name == "OpenRouter":
            if not is_free(m):
                continue
            if isinstance(ctx, int) and ctx < MIN_CTX_OPENROUTER:
                continue
            print(f"FREE  {mid}  ctx={ctx}")
            continue

        candidates.append((mid, ctx))

    if name == "OpenRouter":
        return

    if not PROBE:
        for mid, ctx in candidates:
            print(f"?     {mid}  ctx={ctx}")
        print(f"({len(candidates)} candidates, not verified. Rerun with --probe)")
        return

    shortlist = [c for c in candidates if any(k in c[0].lower() for k in PROBE_KEYWORDS)]
    shortlist = shortlist[:MAX_PROBES_PER_PROVIDER]
    print(f"Probing {len(shortlist)} of {len(candidates)} candidates (1 token each)")
    for mid, ctx in shortlist:
        status = probe(base, key, mid)
        flag = {200: "OK   ", 429: "RATE ", 402: "PAID "}.get(status, "FAIL ")
        print(f"{flag} {mid}  ctx={ctx}  http={status}")
        time.sleep(2)


if __name__ == "__main__":
    for provider, (env_key, base_url) in PROVIDERS.items():
        run(provider, env_key, base_url)