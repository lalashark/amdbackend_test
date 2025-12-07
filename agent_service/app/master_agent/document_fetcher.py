"""Utilities for fetching and parsing documentation content."""
from __future__ import annotations

import re
from typing import Dict, List

import httpx
from bs4 import BeautifulSoup

HTTP_TIMEOUT = 5.0
MAX_TEXT_LENGTH = 12000
API_PATTERN = re.compile(r"\b(?:hip|cuda)[A-Za-z0-9_]+\b")


def fetch_document(url: str) -> Dict[str, object]:
    """Fetch the document at the given URL and extract metadata."""

    try:
        response = httpx.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
    except httpx.HTTPError:
        return {}

    soup = BeautifulSoup(response.text, "html.parser")
    title = _extract_title(soup)
    sections = _extract_sections(soup)
    raw_text = _extract_text(soup)
    api_list = _extract_api_names(raw_text)

    return {
        "title": title,
        "section_headers": sections,
        "raw_text": raw_text,
        "document_category": _guess_category(url, sections),
        "api_list": api_list,
        "section_contents": _extract_section_contents(soup),
    }


def _extract_title(soup: BeautifulSoup) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:200]
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:200]
    return ""


def _extract_sections(soup: BeautifulSoup) -> List[str]:
    sections: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(strip=True)
        if text:
            sections.append(text[:200])
    return sections[:20]


def _extract_text(soup: BeautifulSoup) -> str:
    parts: List[str] = []
    for tag in soup.find_all(["p", "li", "code", "pre"]):
        text = tag.get_text(" ", strip=True)
        if text:
            parts.append(text)
        if sum(len(chunk) for chunk in parts) >= MAX_TEXT_LENGTH:
            break
    return "\n".join(parts)[:MAX_TEXT_LENGTH]


def _extract_api_names(text: str) -> List[str]:
    seen = set()
    api_names: List[str] = []
    for match in API_PATTERN.findall(text):
        if match not in seen:
            seen.add(match)
            api_names.append(match)
        if len(api_names) >= 20:
            break
    return api_names


def _extract_section_contents(soup: BeautifulSoup) -> Dict[str, str]:
    section_map: Dict[str, List[str]] = {}
    current = "Document"
    for element in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = element.get_text(" ", strip=True)
        if not text:
            continue
        if element.name in {"h1", "h2", "h3"}:
            current = text
            section_map.setdefault(current, [])
        else:
            section_map.setdefault(current, []).append(text)
    return {key: "\n".join(values) for key, values in section_map.items()}


def _guess_category(url: str, sections: List[str]) -> str:
    lowered = url.lower()
    if "hip" in lowered:
        return "HIP Documentation"
    if "rocm" in lowered:
        return "ROCm Documentation"
    if any("api" in section.lower() for section in sections):
        return "API Reference"
    return "Technical Document"
