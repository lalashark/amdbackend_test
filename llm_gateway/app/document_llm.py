"""Document summarization via vLLM/OpenAI-compatible endpoint."""
from __future__ import annotations

import asyncio
import json
import unicodedata
from typing import Any, Dict, List

import logging
from openai import OpenAI

from .config import get_settings

logger = logging.getLogger(__name__)
_SETTINGS = get_settings()
_CLIENT = OpenAI(base_url=_SETTINGS.vllm_base_url, api_key=_SETTINGS.vllm_api_key)

RESPONSE_INSTRUCTIONS = """
Write a concise response using exactly these section headers:
- Summary:
- Installation steps:
- Links:

Formatting rules:
- Each bullet must begin with "-" and contain no more than 20 words.
- Provide at most 2 bullets for Summary, 3 bullets for Installation steps, and 2 bullets for Links.
- Include URLs in the Links bullets when available.
- Do not add extra sections, code fences, or commentary.
"""


async def generate_document_summary(request: Dict[str, Any]) -> Dict[str, Any]:
    return await asyncio.to_thread(_generate_sync, request)


def _generate_sync(request: Dict[str, Any]) -> Dict[str, Any]:
    pre = request.get("preprocessed", {})
    title = _sanitize(pre.get("title", "Untitled Document"))
    url = pre.get("url", "")
    sections = [_sanitize(section) for section in pre.get("section_headers", [])]
    api_list = [_sanitize(api) for api in pre.get("api_list", [])]
    section_contents = pre.get("section_contents", {})
    context_text = _sanitize(_build_context_snippet(section_contents, pre.get("raw_text", "")))

    user_prompt = _build_prompt(title, url, sections, api_list, context_text)

    primary_messages = [
        {
            "role": "system",
            "content": (
                "You are AMDlingo's Document Worker Agent. "
                "Summarize AMD/ROCm technical docs into very short bullets."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    content = _call_chat(primary_messages)
    parsed = _parse_structured_text(content)
    if parsed:
        parsed["context_sync_key"] = request.get("session_id", "")
        return parsed

    logger.warning("Primary document prompt failed, retrying with simplified prompt")
    simplified_prompt = _build_simplified_prompt(title, url, context_text, sections)
    simplified_messages = [
        {
            "role": "system",
            "content": (
                "You summarize AMD documentation into short bullet lists."
            ),
        },
        {"role": "user", "content": simplified_prompt},
    ]
    content = _call_chat(simplified_messages)
    parsed = _parse_structured_text(content)
    if parsed:
        parsed["context_sync_key"] = request.get("session_id", "")
        return parsed

    return _fallback_response(request)


def _call_chat(messages: List[Dict[str, str]]) -> str:
    response = _CLIENT.chat.completions.create(
        model=_SETTINGS.vllm_model_id,
        messages=messages,
        temperature=0.2,
        max_tokens=800,
    )
    content = response.choices[0].message.content or ""
    print("[document_llm] raw response:", content)
    return content


def _build_context_snippet(section_contents: Dict[str, str], raw_text: str) -> str:
    def _pick(names: List[str]) -> str:
        for name in names:
            if name in section_contents:
                return section_contents[name]
        return ""

    prereq = _pick(["Prerequisites#", "Prerequisites #", "Prerequisites"])
    install = _pick(["Installation#", "Installation #", "Installation"])
    verify = _pick(["Verify your installation#", "Verify your installation #", "Verify your installation"])

    blocks = []
    if prereq:
        blocks.append("Prerequisites:\n" + prereq[:1000])
    if install:
        blocks.append("Installation:\n" + install[:1500])
    if verify:
        blocks.append("Verification:\n" + verify[:800])

    if not blocks and raw_text:
        return raw_text[:3000]

    return "\n\n".join(blocks)[:3500]


def _sanitize(text: str) -> str:
    """Normalize unicode text to ASCII to avoid vLLM returning garbage symbols."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return normalized.encode("ascii", "ignore").decode("ascii")


def _format_result(summary: str, installations: List[str], links: List[str]) -> Dict[str, Any]:
    return {
        "summary": summary,
        "api_explanations": [],
        "key_points": list(installations)[:3],
        "pitfalls": [],
        "concept_links": list(links)[:2],
        "example_code": "",
        "notes": "",
        "context_sync_key": "",
    }


def _build_prompt(
    title: str, url: str, sections: List[str], api_list: List[str], context_text: str
) -> str:
    section_text = "\n".join(f"- {sec}" for sec in sections[:10]) or "- (not provided)"
    api_text = ", ".join(api_list[:10]) or "(none)"
    instructions = RESPONSE_INSTRUCTIONS.strip()
    return (
        f"{instructions}\n\n"
        f"Document Title: {title}\n"
        f"Source URL: {url or 'N/A'}\n"
        f"Section headers:\n{section_text}\n"
        f"Mentioned APIs: {api_text}\n"
        "Document content:\n"
        f"{context_text}\n"
        "Produce the JSON summary now. Limit summary to 3 sentences and include at most 4 entries for installation_steps, prerequisites, verification, and links."
    )


def _build_simplified_prompt(
    title: str, url: str, context_text: str, sections: List[str]
) -> str:
    section_text = "\n".join(f"- {sec}" for sec in sections[:5]) or "- (not provided)"
    trimmed_text = context_text[:4000]
    simplified_prompt = (
        f"{RESPONSE_INSTRUCTIONS.strip()}\n\n"
        f"Document Title: {title}\n"
        f"Source URL: {url or 'N/A'}\n"
        f"Section headers:\n{section_text}\n"
        "Document content:\n"
        f"{trimmed_text}\n"
        "Produce the bullet-format summary exactly as instructed using the exact headers."
    )
    return simplified_prompt


def _parse_structured_text(content: str) -> Dict[str, Any]:
    json_candidate = _attempt_json_parse(content)
    if json_candidate:
        return json_candidate

    exact_sections = {"summary": [], "installation": [], "links": []}
    current = None
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith("summary"):
            current = "summary"
            continue
        if lowered.startswith("installation"):
            current = "installation"
            continue
        if lowered.startswith("links"):
            current = "links"
            continue
        if current:
            cleaned = line.lstrip("-*•0123456789. ").strip()
            if cleaned:
                exact_sections[current].append(cleaned)
    if exact_sections["summary"] or exact_sections["installation"]:
        summary_text = " ".join(exact_sections["summary"][:2])
        installation = exact_sections["installation"][:3]
        links = exact_sections["links"][:2]
        return _format_result(summary_text, installation, links)

    # Fallback parser for generic markdown sections like "**Install HIP**"
    generic = _parse_markdown_sections(content)
    if generic:
        return generic

    return {}


def _attempt_json_parse(content: str) -> Dict[str, Any]:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        return {}
    snippet = content[start : end + 1]
    try:
        data = json.loads(snippet)
    except json.JSONDecodeError:
        return {}
    summary = data.get("summary", "")
    install = data.get("installation_steps", [])
    links = data.get("links", [])
    return _format_result(summary, install, links)


def _fallback_response(request: Dict[str, Any]) -> Dict[str, Any]:
    pre = request.get("preprocessed", {})
    session_id = request.get("session_id", "")
    raw_text = pre.get("raw_text", "")
    section_contents = pre.get("section_contents", {})
    print("[fallback] section keys:", list(section_contents.keys())[:10])
    summary = _extract_summary(raw_text, section_contents)
    key_points = _extract_key_points(section_contents)
    concept_links = pre.get("section_headers", [])[:5]
    api_list = pre.get("api_list", [])[:3]
    api_explanations = [
        {
            "name": api,
            "description": "Refer to official ROCm docs for details.",
            "parameters": "See documentation",
            "return": "",
            "common_pitfalls": [],
            "example_code": "",
        }
        for api in api_list
    ]
    result = {
        "summary": summary or "Unable to summarize the document.",
        "api_explanations": api_explanations,
        "key_points": key_points,
        "pitfalls": [],
        "concept_links": concept_links,
        "example_code": "",
        "notes": "Fallback response without LLM.",
        "context_sync_key": session_id,
    }
    return result


def _parse_markdown_sections(content: str) -> Dict[str, Any]:
    sections: Dict[str, List[str]] = {}
    current_key = None

    def _normalize_key(raw: str | None) -> str | None:
        if not raw:
            return None
        cleaned = raw.strip().lower()
        return cleaned or None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        heading = None
        if line.startswith("**") and line.endswith("**"):
            heading = line.strip("* ")
        elif line.endswith(":") and len(line) < 80:
            heading = line.strip(": ")

        if heading:
            current_key = _normalize_key(heading)
            sections.setdefault(current_key or "summary", [])
            continue

        if line[:1] in {"-", "*"}:
            bullet = line.lstrip("-*•0123456789. ").strip()
            if bullet:
                key = current_key or "summary"
                sections.setdefault(key, []).append(bullet)

    if not sections:
        return {}

    summary_lines = sections.get("summary")
    if not summary_lines:
        summary_lines = next(iter(sections.values()))

    install_lines: List[str] = []
    link_lines: List[str] = []
    for key, bullets in sections.items():
        if key and any(word in key for word in ("install", "installation", "step")):
            install_lines.extend(bullets)
        if key and "link" in key:
            link_lines.extend(bullets)
        for bullet in bullets:
            if "http://" in bullet.lower() or "https://" in bullet.lower():
                link_lines.append(bullet)

    if not install_lines:
        remaining = summary_lines[2:] + [
            bullet for key, bullets in sections.items() if key != "summary" for bullet in bullets
        ]
        install_lines = remaining

    summary_text = " ".join(summary_lines[:2])
    return _format_result(summary_text, install_lines[:3], link_lines[:2])


def _extract_summary(raw_text: str, sections: Dict[str, str]) -> str:
    install = sections.get("Installation#") or sections.get("Installation #") or sections.get("Installation")
    if install:
        return install[:600]
    if raw_text:
        import re

        sentences = re.split(r"(?<=[。\.！!？?])\s+", raw_text)
        return " ".join(sentences[:3])[:600]
    return ""


def _extract_key_points(sections: Dict[str, str]) -> List[str]:
    points: List[str] = []
    heading_aliases = [
        "Prerequisites#",
        "Prerequisites #",
        "Prerequisites",
        "Installation#",
        "Installation #",
        "Installation",
        "Verify your installation#",
        "Verify your installation #",
        "Verify your installation",
    ]
    for heading in heading_aliases:
        content = sections.get(heading)
        if not content:
            continue
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            points.append(f"{heading.rstrip('#')}: {stripped}")
            if len(points) >= 5:
                return points
    return points
