"""
ocr_service.py — LLM-based document & image extraction.
Supports OpenAI GPT-4o Vision and Google Gemini 1.5 Flash.
"""
from __future__ import annotations
import base64
import json
import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _encode_image(image_path: str) -> str:
    """Base64-encode an image file for API submission."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


EXTRACTION_PROMPT = """
You are an expert insurance claims examiner. Analyse the provided image/document and extract the following fields as a JSON object:
{
  "document_type": "receipt | damage_photo | medical_report | police_report | other",
  "claim_date": "YYYY-MM-DD or null",
  "claimed_amount": <number or null>,
  "description_summary": "<1-2 sentence summary>",
  "provider_name": "<hospital/shop/garage name or null>",
  "confidence_score": <0.0-1.0>,
  "red_flags": ["<any suspicious elements observed>"]
}
Return ONLY valid JSON. No prose, no markdown fences.
"""


def extract_from_image_openai(image_path: str) -> dict:
    """Use OpenAI GPT-4o Vision to extract structured data from an image."""
    import openai  # lazy import

    client = openai.OpenAI(api_key=settings.openai_api_key)
    b64 = _encode_image(image_path)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                ],
            }
        ],
        max_tokens=512,
        temperature=0,
    )
    raw = response.choices[0].message.content.strip()
    return json.loads(raw)


def extract_from_image_gemini(image_path: str) -> dict:
    """Use Google Gemini 1.5 Flash to extract structured data from an image."""
    import google.generativeai as genai  # lazy import

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    with open(image_path, "rb") as f:
        image_bytes = f.read()

    import PIL.Image
    import io
    pil_img = PIL.Image.open(io.BytesIO(image_bytes))

    response = model.generate_content([EXTRACTION_PROMPT, pil_img])
    raw = response.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def extract_document_data(image_paths: list[str]) -> dict:
    """
    Main entry point. Tries configured LLM provider; falls back gracefully.
    Merges results across multiple uploaded images.
    """
    if not image_paths:
        return _empty_extraction()

    results = []
    for path in image_paths[:3]:  # Limit to first 3 images
        try:
            if settings.llm_provider == "gemini" and settings.gemini_api_key:
                result = extract_from_image_gemini(path)
            elif settings.openai_api_key:
                result = extract_from_image_openai(path)
            else:
                logger.warning("No LLM API key configured — using mock extraction.")
                result = _mock_extraction(path)
            results.append(result)
        except Exception as e:
            logger.error(f"LLM extraction failed for {path}: {e}")
            results.append(_empty_extraction())

    return _merge_results(results)


def _merge_results(results: list[dict]) -> dict:
    """Merge extraction results from multiple images, taking highest confidence."""
    if not results:
        return _empty_extraction()
    best = max(results, key=lambda r: r.get("confidence_score", 0))
    # Aggregate red flags
    all_flags = []
    for r in results:
        all_flags.extend(r.get("red_flags", []))
    best["red_flags"] = list(set(all_flags))
    best["image_count"] = len(results)
    return best


def _mock_extraction(image_path: str) -> dict:
    """Deterministic mock for development / no-API-key mode."""
    return {
        "document_type": "damage_photo",
        "claim_date": None,
        "claimed_amount": None,
        "description_summary": "Image uploaded — LLM extraction unavailable (mock mode).",
        "provider_name": None,
        "confidence_score": 0.5,
        "red_flags": [],
        "mock": True,
    }


def _empty_extraction() -> dict:
    return {
        "document_type": "other",
        "claim_date": None,
        "claimed_amount": None,
        "description_summary": "",
        "provider_name": None,
        "confidence_score": 0.0,
        "red_flags": [],
    }
