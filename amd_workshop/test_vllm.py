import json
from typing import List

import requests
from openai import OpenAI

VLLM_ENDPOINTS: List[str] = [
    "http://210.61.209.139:45014/v1/",
    "http://210.61.209.139:45005/v1/",
]


def discover_model() -> tuple[str, str]:
    for base_url in VLLM_ENDPOINTS:
        try:
            response = requests.get(base_url + "models", timeout=5)
            response.raise_for_status()
            payload = response.json()
            print(f"Connected to {base_url} | Response: {json.dumps(payload, ensure_ascii=False)}")
            models = payload.get("data") or []
            if models:
                model_id = models[0].get("id", "gpt-oss-120b")
            else:
                model_id = "gpt-oss-120b"
            return base_url, model_id
        except Exception as exc:
            print(f"Failed connecting to {base_url}: {exc}")
    raise RuntimeError("Unable to reach any vLLM endpoint")


def run_completions(client: OpenAI, model: str) -> None:
    prompt = "Once upon a time in a magical forest,"
    print("=== Completion Test ===")
    response = client.completions.create(
        model=model,
        prompt=prompt,
        max_tokens=100,
        temperature=0.8,
    )
    print("Prompt:", prompt)
    print("Generated text:", response.choices[0].text)


def run_chat(client: OpenAI, model: str) -> None:
    print("=== Chat Test ===")
    chat = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Explain machine learning in one paragraph."},
        ],
        temperature=0.7,
    )
    print("Chat response:", chat.choices[0].message.content)


def run_reasoning(client: OpenAI, model: str) -> None:
    print("=== Reasoning Test ===")
    question = """
Solve this logic puzzle step by step:

Three friends - Alice, Bob, and Carol - each have a different pet (cat, dog, bird) and live in different colored houses (red, blue, green).

Clues:
1. Alice doesn't live in the red house
2. The person with the cat lives in the blue house
3. Bob doesn't have a bird
4. Carol doesn't live in the green house
5. The person in the red house has a dog

Who has which pet and lives in which house?
"""
    reasoning = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an expert problem solver. Think step by step and show your reasoning process.",
            },
            {"role": "user", "content": question},
        ],
        temperature=0.1,
        max_tokens=500,
    )
    print("Reasoning response:", reasoning.choices[0].message.content)


def main() -> None:
    base_url, model_name = discover_model()
    print(f"Using endpoint: {base_url}, model: {model_name}")
    client = OpenAI(base_url=base_url, api_key="dummy-key")
    run_completions(client, model_name)
    run_chat(client, model_name)
    run_reasoning(client, model_name)


if __name__ == "__main__":
    main()
