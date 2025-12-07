import requests
from openai import OpenAI

ENDPOINT = "http://210.61.209.139:45014/v1/"
MODEL = "openai/gpt-oss-120b"

client = OpenAI(base_url=ENDPOINT, api_key="dummy-key")

system_prompt = "You are a helpful math tutor. Solve problems step by step."
user_prompt = "A train travels 120 km in 2 hours. If it maintains the same speed, how far will it travel in 5 hours? Please show your work."

response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ],
    temperature=0.3,
    max_tokens=200,
    reasoning_effort="high",
)

print("Prompt:", user_prompt)
print("\nResponse:\n", response.choices[0].message.content)
