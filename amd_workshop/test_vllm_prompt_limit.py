import math
from typing import List

from openai import OpenAI
import requests

ENDPOINTS: List[str] = [
    "http://210.61.209.139:45014/v1/",
    "http://210.61.209.139:45005/v1/",
]


def discover_model() -> tuple[str, str]:
    for base_url in ENDPOINTS:
        try:
            resp = requests.get(base_url + "models", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data") or []
            model_id = models[0]["id"] if models else "openai/gpt-oss-120b"
            print(f"Connected to {base_url}, model={model_id}")
            return base_url, model_id
        except Exception as exc:
            print(f"Failed {base_url}: {exc}")
    raise RuntimeError("No vLLM endpoint reachable")


def run_length_sweep(client: OpenAI, model: str) -> None:
    lengths = [200, 500, 1000, 2000, 3000, 4000, 5000, 6000]
    base_sentence = (
        "HIP installs via ROCm. Follow prerequisites, install packages, set HIP_PATH. "
    )
    for length in lengths:
        repeat = math.ceil(length / len(base_sentence))
        prompt = "Length test ({} chars): ".format(length) + base_sentence * repeat
        prompt = prompt[:length]
        try:
            resp = client.completions.create(
                model=model,
                prompt=prompt,
                max_tokens=64,
                temperature=0.4,
            )
            text = resp.choices[0].text
            status = "OK"
            if text.count("!") > 50:
                status = "EXCLAMATION"
            print(f"len={length} -> status={status} output={text[:80]!r}")
        except Exception as exc:
            print(f"len={length} -> error {exc}")


def main() -> None:
    base_url, model = discover_model()
    client = OpenAI(base_url=base_url, api_key="dummy-key")
    run_length_sweep(client, model)


if __name__ == "__main__":
    main()
