import requests
from openai import OpenAI

DOC_URL = "https://rocm.docs.amd.com/projects/HIP/en/latest/install/install.html"
JSON_SCHEMA_DESCRIPTION = """
Return a JSON object strictly matching this schema:
{
  "summary": string,
  "api_explanations": [
     {
        "name": string,
        "description": string,
        "parameters": string,
        "return": string,
        "common_pitfalls": [string],
        "example_code": string
     }
  ],
  "key_points": [string],
  "pitfalls": [string],
  "concept_links": [string],
  "example_code": string,
  "notes": string,
  "context_sync_key": string
}
Ensure the output is valid JSON without code fences.
"""

SYSTEM_PROMPT = (
    "You are AMDlingo's Document Worker Agent. Summarize AMD/ROCm technical docs, "
    "explain APIs, generate examples, and produce JSON."
)


def fetch_doc() -> str:
    resp = requests.get(DOC_URL, timeout=15)
    resp.raise_for_status()
    return resp.text


def main() -> None:
    html = fetch_doc()
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    text = "\n".join(tag.get_text(" ", strip=True) for tag in soup.find_all(["p", "li", "code", "pre"]))
    text = text[:8000]
    sections = [tag.get_text(strip=True) for tag in soup.find_all(["h1", "h2", "h3"])][:10]
    api_list = []
    user_prompt = (
        f"Document Title: Install HIP\n"
        f"Source URL: {DOC_URL}\n"
        f"Section headers:\n" + "\n".join(f"- {sec}" for sec in sections) + "\n"
        f"Mentioned APIs: {', '.join(api_list) if api_list else '(none)'}\n"
        "Document content:\n"
        f"{text}\n"
        "Produce the JSON summary now."
    )

    base_url = "http://210.61.209.139:45014/v1/"
    client = OpenAI(base_url=base_url, api_key="dummy-key")

    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": JSON_SCHEMA_DESCRIPTION},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=800,
    )
    print("RAW RESPONSE:\n", response.choices[0].message.content)


if __name__ == "__main__":
    main()
