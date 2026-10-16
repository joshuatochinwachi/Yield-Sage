"""
List live models per provider.
Groq, SambaNova, Cerebras, NVIDIA, Gemini, OpenRouter.
Uses each provider's OpenAI-compatible GET /models endpoint.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

PROVIDERS = {
    "Groq": {
        "env_key": "GROQ_API_KEY",
        "url": "https://api.groq.com/openai/v1/models",
    },
    "SambaNova": {
        "env_key": "SAMBANOVA_API_KEY",
        "url": "https://api.sambanova.ai/v1/models",
    },
    "Cerebras": {
        "env_key": "CEREBRAS_API_KEY",
        "url": "https://api.cerebras.ai/v1/models",
    },
    "NVIDIA": {
        "env_key": "NVIDIA_API_KEY",
        "url": "https://integrate.api.nvidia.com/v1/models",
    },
    "Gemini": {
        "env_key": "GEMINI_API_KEY",
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/models",
    },
    "OpenRouter": {
        "env_key": "OPENROUTER_API_KEY",
        "url": "https://openrouter.ai/api/v1/models",
        "free_only": True,
    },
}

# Skip models that are not text chat models
SKIP_WORDS = (
    "whisper", "tts", "guard", "embed", "orpheus", "transcribe", "moderation",
    "imagen", "veo", "lyria", "image", "aqa", "safety", "rerank", "vision-only",
    "retriever", "parse", "clip",
)

MIN_CTX_OPENROUTER = 16000  # your prompt is ~8K, leave room for output


def is_free(m: dict) -> bool:
    p = m.get("pricing") or {}
    try:
        return float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0
    except (TypeError, ValueError):
        return False


def list_models(name: str, cfg: dict) -> None:
    print(f"\n=== {name} ===")
    key = os.getenv(cfg["env_key"])
    if not key:
        print(f"SKIPPED: {cfg['env_key']} not set")
        return

    try:
        r = requests.get(
            cfg["url"],
            headers={"Authorization": f"Bearer {key}"},
            timeout=30,
        )
    except requests.RequestException as e:
        print(f"REQUEST FAILED: {e}")
        return

    if r.status_code != 200:
        print(f"HTTP {r.status_code}: {r.text[:200]}")
        return

    models = r.json().get("data", [])
    if not models:
        print("No models returned.")
        return

    shown = 0
    for m in sorted(models, key=lambda x: x.get("id", "")):
        mid = m.get("id", "")

        # Gemini returns ids like "models/gemini-2.5-flash"; strip the prefix
        if name == "Gemini" and mid.startswith("models/"):
            mid = mid[len("models/"):]

        if any(w in mid.lower() for w in SKIP_WORDS):
            continue

        ctx = m.get("context_window") or m.get("context_length") or "?"

        if cfg.get("free_only"):
            if not is_free(m):
                continue
            if isinstance(ctx, int) and ctx < MIN_CTX_OPENROUTER:
                continue

        print(f"{mid}  ctx={ctx}")
        shown += 1

    print(f"({shown} shown of {len(models)} total)")


if __name__ == "__main__":
    for provider, config in PROVIDERS.items():
        list_models(provider, config)