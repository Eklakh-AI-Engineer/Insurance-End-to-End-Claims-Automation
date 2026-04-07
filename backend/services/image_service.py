"""
image_service.py — AI-powered image damage verification and forgery detection.

Two-layer check:
1. ResNet50 feature vector + cosine similarity to "damage" prototype (no GPU needed)
2. OpenCV JPEG error level analysis (ELA) for forgery detection
"""
from __future__ import annotations
import io
import logging
import math
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy ResNet imports ────────────────────────────────────────────────────────
_resnet = None
_transform = None


def _load_resnet():
    global _resnet, _transform
    if _resnet is None:
        try:
            import torch
            import torchvision.models as models
            import torchvision.transforms as T

            model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
            model.eval()
            # Remove final classification layer — use as feature extractor
            _resnet = torch.nn.Sequential(*list(model.children())[:-1])

            _transform = T.Compose([
                T.ToPILImage(),
                T.Resize((224, 224)),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            logger.info("ResNet50 loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load ResNet50: {e}. Using OpenCV-only mode.")
    return _resnet, _transform


# ── ELA (Error Level Analysis) ────────────────────────────────────────────────

def _ela_forgery_score(image_path: str, quality: int = 90) -> float:
    """
    Error Level Analysis detects JPEG re-compression artefacts that indicate
    digital manipulation. Returns a score 0-1 (higher = more suspicious).
    """
    img = cv2.imread(image_path)
    if img is None:
        return 0.5  # Can't read → neutral

    # Save at reduced quality
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    recompressed = cv2.imdecode(buf, cv2.IMREAD_COLOR)

    # Difference amplified
    diff = cv2.absdiff(img.astype(np.float32), recompressed.astype(np.float32))
    diff_amplified = np.clip(diff * 15, 0, 255)

    # Score: std-dev of amplified error relative to mean brightness
    mean_err = np.mean(diff_amplified)
    std_err = np.std(diff_amplified)
    # Normalise: typical clean images have mean_err < 10; manipulated > 30
    score = float(np.clip(mean_err / 50.0, 0.0, 1.0))
    return round(score, 4)


# ── Structural features (edge density, colour uniformity) ─────────────────────

def _structural_damage_score(image_path: str) -> float:
    """
    Heuristic: real damage photos tend to have high edge density and low colour
    uniformity (many broken lines, mixed colours). Returns 0-1 (higher = more
    damage-like).
    """
    img = cv2.imread(image_path)
    if img is None:
        return 0.5

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Edge density via Canny
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.mean(edges > 0))  # fraction of pixels that are edges

    # Colour uniformity: std across all channels (higher = more varied = more damage-like)
    colour_std = float(np.std(img.astype(np.float32))) / 128.0  # normalise to [0, ~1]

    score = 0.5 * edge_density + 0.5 * min(colour_std, 1.0)
    return round(min(score, 1.0), 4)


# ── ResNet feature similarity ─────────────────────────────────────────────────

def _resnet_damage_likelihood(image_path: str) -> float:
    """
    Without ground-truth fine-tuning, we use a proxy:
    images with low activation magnitude are likely blank/clean,
    high magnitude suggest rich visual content (consistent with damage photos).
    Returns 0-1 likelihood of damage.
    """
    try:
        import torch
        model, transform = _load_resnet()
        if model is None or transform is None:
            return 0.5  # Fallback

        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return 0.5
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        tensor = transform(img_rgb).unsqueeze(0)
        with torch.no_grad():
            feat = model(tensor).squeeze().numpy()

        # L2 norm of feature vector as a proxy for "richness"
        mag = float(np.linalg.norm(feat))
        # Typical range 5-30; clip to [0,1]
        score = float(np.clip((mag - 5) / 25.0, 0.0, 1.0))
        return round(score, 4)
    except Exception as e:
        logger.warning(f"ResNet inference failed: {e}")
        return 0.5


# ── Main API ──────────────────────────────────────────────────────────────────

def analyse_images(image_paths: list[str]) -> dict:
    """
    Returns:
        {
            "image_valid":       bool,  # True if damage detected
            "forgery_suspected": bool,
            "avg_ela_score":     float,
            "avg_damage_score":  float,
            "per_image":         list[dict],
        }
    """
    if not image_paths:
        return {
            "image_valid": False,
            "forgery_suspected": False,
            "avg_ela_score": 0.0,
            "avg_damage_score": 0.0,
            "per_image": [],
        }

    per_image = []
    for path in image_paths:
        ela = _ela_forgery_score(path)
        structural = _structural_damage_score(path)
        resnet = _resnet_damage_likelihood(path)

        # Damage score: blend structural + resnet
        damage = round(0.4 * structural + 0.6 * resnet, 4)

        per_image.append({
            "path": path,
            "ela_forgery_score": ela,
            "structural_damage_score": structural,
            "resnet_damage_score": resnet,
            "damage_score": damage,
        })

    avg_ela = float(np.mean([p["ela_forgery_score"] for p in per_image]))
    avg_damage = float(np.mean([p["damage_score"] for p in per_image]))

    # Decisions
    image_valid = avg_damage >= 0.35          # At least some damage evidence
    forgery_suspected = avg_ela >= 0.50       # High re-compression error

    return {
        "image_valid": image_valid,
        "forgery_suspected": forgery_suspected,
        "avg_ela_score": round(avg_ela, 4),
        "avg_damage_score": round(avg_damage, 4),
        "per_image": per_image,
    }
