from openai import OpenAI
import requests

DOC_URL = "https://rocm.docs.amd.com/projects/HIP/en/latest/install/install.html"
client = OpenAI(base_url="http://210.61.209.139:45014/v1/", api_key="dummy-key")
model = "openai/gpt-oss-120b"

resp = requests.get(DOC_URL, timeout=10)
resp.raise_for_status()
text = resp.text[:4000]

system_prompt = "You are AMDlingo's assistant. Write short bullets."
user_prompt = (
    "Summarize the HIP installation page in 2 summary bullets, 3 installation steps, and 2 links."
    " Use short sentences. Data:\n" + text
)

response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    temperature=0.2,
    max_tokens=300
)
print(response.choices[0].message.content)
