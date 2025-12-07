import requests
from bs4 import BeautifulSoup

url = "https://rocm.docs.amd.com/projects/HIP/en/latest/install/install.html"
resp = requests.get(url, timeout=15)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")
for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
    text = tag.get_text(strip=True)
    if text:
        print(f"{tag.name.upper()}: {text}")
