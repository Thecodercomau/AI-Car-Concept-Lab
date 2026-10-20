from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

import requests
from flask import Flask, jsonify, render_template, request, session

try:
    from groq import Groq
except ImportError:  # pragma: no cover - optional runtime dependency
    Groq = None

from config import (
    FLASK_SECRET_KEY,
    GROQ_API_KEY,
    GROQ_MODEL,
    HCAPTCHA_SECRET_KEY,
    HCAPTCHA_SITE_KEY,
)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["SESSION_PERMANENT"] = False

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY and Groq else None
MAX_HISTORY = 12

STYLE_TAGS = {
    "Hypercar": ["aggressive aero", "track-born drama", "hero stance"],
    "Luxury": ["quiet prestige", "clean surfacing", "executive cabin"],
    "Off-Road": ["all-terrain muscle", "raised stance", "rugged utility"],
    "EV": ["clean tech", "silent thrust", "future cockpit"],
    "Retro-Future": ["heritage remix", "neo-classic curves", "concept nostalgia"],
    "Street": ["night-run energy", "urban custom", "after-dark attitude"],
}

MATERIAL_NOTES = {
    "Carbon Fiber": ["carbon composite shell", "forged aero fins", "lightweight chassis"],
    "Aluminum": ["aluminum body frame", "precision-machined trim", "satin shell panels"],
    "Titanium": ["titanium highlights", "heat-blued metal details", "ultra-premium structural spine"],
    "Recycled Composite": ["recycled composite shell", "eco-performance weave", "sustainable cabin accents"],
    "Glass & Metal": ["glass canopy roof", "brushed alloy bodywork", "framed light signature"],
    "Mixed Performance": ["hybrid material shell", "performance mesh venting", "contrasting aero textures"],
}

PRICE_BANDS = {
    "Daily Drive": "$58,000",
    "Track Day": "$210,000",
    "Adventure": "$96,000",
    "Collector Reveal": "$320,000",
    "City Tech": "$74,000",
    "Luxury Tourer": "$168,000",
}

DESIGN_PROMPT = """You are a visionary automotive concept designer.
Generate a complete futuristic car concept based on:
Style: {style}
Primary Color: {primary_color}
Accent Color: {accent_color}
Material: {material}
Occasion: {occasion}
Inspiration: {inspiration}

Respond with raw JSON only — no markdown, no explanation.
{{
  "name": "2-4 word creative car name",
  "tagline": "punchy tagline max 10 words",
  "description": "2-3 sentence cinematic concept description",
  "materials": ["mat1", "mat2", "mat3"],
  "colorways": [
    {{"name": "launch spec", "body": "#hex", "accent": "#hex", "wheels": "#hex", "cabin": "#hex"}}
  ],
  "features": ["feat1", "feat2", "feat3", "feat4"],
  "powertrain": "power system description",
  "cockpit_theme": "cockpit mood and interface idea",
  "target_driver": "who this concept is for",
  "retail_price": "$XXX,XXX",
  "style_tags": ["tag1", "tag2", "tag3"]
}}
Generate exactly 3 colorways. All hex codes must be valid #RRGGBB."""


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/studio")
def studio() -> str:
    return render_template("studio.html", hcaptcha_site_key=HCAPTCHA_SITE_KEY)


@app.route("/history")
def history() -> str:
    return render_template("history.html", designs=get_history())


@app.route("/generate", methods=["POST"])
def generate() -> Any:
    data = request.get_json(silent=True) or request.form
    prefs = get_prefs(data)
    if any(not v for v in prefs.values()):
        return jsonify({"error": "Please complete every field in the design brief."}), 400

    if not session.pop("hcaptcha_verified", False):
        captcha_error = verify_hcaptcha(data)
        if captcha_error:
            message, status = captcha_error
            return jsonify({"error": message}), status

    submitted_concept = data.get("concept")
    if submitted_concept is not None:
        if not is_valid_concept(submitted_concept):
            return jsonify({"error": "Generated concept has an invalid format."}), 400
        concept = sanitize_concept(submitted_concept, prefs)
    else:
        try:
            concept = generate_concept(prefs)
        except json.JSONDecodeError as exc:
            return jsonify({"error": f"Malformed AI response: {exc}"}), 500
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"Concept generation failed: {exc}"}), 500

    concept["image_url"] = build_image_url(concept, prefs)
    concept["brief"] = prefs
    concept["timestamp"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    concept["fingerprint"] = fingerprint(prefs, concept["name"])
    add_to_history(concept)
    return jsonify({"success": True, "concept": concept, "prefs": prefs})


@app.route("/verify-captcha", methods=["POST"])
def verify_captcha() -> Any:
    data = request.get_json(silent=True) or {}
    captcha_error = verify_hcaptcha(data)
    if captcha_error:
        message, status = captcha_error
        return jsonify({"error": message}), status
    session["hcaptcha_verified"] = True
    return jsonify({"success": True})


def verify_hcaptcha(data: Any) -> tuple[str, int] | None:
    if not HCAPTCHA_SITE_KEY and not HCAPTCHA_SECRET_KEY:
        return None
    if not HCAPTCHA_SITE_KEY or not HCAPTCHA_SECRET_KEY:
        return "CAPTCHA is not configured correctly.", 503

    captcha_token = str(getattr(data, "get", lambda *_: "")("h-captcha-response", "")).strip()
    if not captcha_token:
        return "Please complete the CAPTCHA.", 400

    try:
        verification_response = requests.post(
            "https://api.hcaptcha.com/siteverify",
            data={"secret": HCAPTCHA_SECRET_KEY, "response": captcha_token},
            timeout=5,
        )
        verification_response.raise_for_status()
        verification = verification_response.json()
    except (requests.RequestException, ValueError):
        return "CAPTCHA verification is temporarily unavailable. Please try again.", 503

    if not isinstance(verification, dict):
        return "CAPTCHA verification is temporarily unavailable. Please try again.", 503
    if verification.get("success") is not True:
        return "CAPTCHA verification failed. Please try again.", 400
    return None


@app.route("/clear-history", methods=["POST"])
def clear_history() -> Any:
    session["designs"] = []
    session.modified = True
    return jsonify({"success": True})


def get_prefs(data: Any) -> dict[str, str]:
    fields = [
        ("style", "Hypercar"),
        ("primary_color", "#1d4ed8"),
        ("accent_color", "#f97316"),
        ("material", "Carbon Fiber"),
        ("occasion", "City Tech"),
        ("inspiration", "Tokyo neon rain"),
    ]
    return {k: str(getattr(data, 'get', lambda *_: d)(k, d)).strip() for k, d in fields}


def get_history() -> list[dict[str, Any]]:
    return session.get("designs", [])


def add_to_history(concept: dict[str, Any]) -> None:
    current = session.get("designs", [])
    deduped = [d for d in current if d.get("fingerprint") != concept["fingerprint"]]
    session["designs"] = [concept] + deduped[: MAX_HISTORY - 1]
    session.modified = True


def fingerprint(prefs: dict[str, str], name: str) -> str:
    raw = "|".join([*prefs.values(), name])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]


def generate_concept(prefs: dict[str, str]) -> dict[str, Any]:
    if groq_client:
        concept = generate_via_groq(prefs)
        if concept:
            return concept
    return generate_local_concept(prefs)


def generate_via_groq(prefs: dict[str, str]) -> dict[str, Any] | None:
    raw = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": "Automotive concept design expert. Pure JSON only."},
            {"role": "user", "content": DESIGN_PROMPT.format(**prefs)},
        ],
        temperature=0.85,
        max_tokens=1200,
    ).choices[0].message.content.strip()

    cleaned = clean_ai_json_text(raw)
    concept = json.loads(cleaned)
    if not is_valid_concept(concept):
        return None
    return sanitize_concept(concept, prefs)


def clean_ai_json_text(raw: str) -> str:
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    return match.group(0) if match else raw


def is_valid_concept(concept: dict[str, Any]) -> bool:
    required = {
        "name", "tagline", "description", "materials", "features", "powertrain",
        "cockpit_theme", "target_driver", "retail_price", "style_tags", "colorways",
    }
    if not isinstance(concept, dict) or not required.issubset(concept):
        return False
    text_fields = required - {"materials", "features", "style_tags", "colorways"}
    return (
        all(isinstance(concept[field], str) and concept[field].strip() for field in text_fields)
        and all(isinstance(concept[field], list) for field in ("materials", "features", "style_tags", "colorways"))
        and all(isinstance(item, str) for field in ("materials", "features", "style_tags") for item in concept[field])
        and all(isinstance(item, dict) for item in concept["colorways"])
    )


def sanitize_concept(concept: dict[str, Any], brief: dict[str, str]) -> dict[str, Any]:
    return {
        "name": str(concept.get("name", "Concept X")).strip(),
        "tagline": str(concept.get("tagline", "Future in motion.")).strip(),
        "description": str(concept.get("description", "")).strip(),
        "materials": [str(x).strip() for x in concept.get("materials", [])][:5] or MATERIAL_NOTES.get(brief["material"], [])[:3],
        "features": [str(x).strip() for x in concept.get("features", [])][:6] or [
            "Adaptive aero body surfaces", "Panoramic digital cockpit", "Active rear light blade", "Predictive drive intelligence"
        ],
        "powertrain": str(concept.get("powertrain", "Quad-motor electric performance")).strip(),
        "cockpit_theme": str(concept.get("cockpit_theme", "Minimal driver-first cockpit")).strip(),
        "target_driver": str(concept.get("target_driver", "Design-forward performance drivers")).strip(),
        "retail_price": str(concept.get("retail_price", PRICE_BANDS.get(brief["occasion"], "$120,000"))).strip(),
        "style_tags": [str(x).strip() for x in concept.get("style_tags", [])][:3] or STYLE_TAGS.get(brief["style"], [])[:3],
        "colorways": normalize_colorways(concept.get("colorways", []), brief),
    }


def normalize_colorways(colorways: list[dict[str, Any]], brief: dict[str, str]) -> list[dict[str, str]]:
    fallback = [
        {"name": "Launch Spec", "body": brief["primary_color"], "accent": brief["accent_color"], "wheels": "#1b1e28", "cabin": "#d9dce5"},
        {"name": "Midnight Pulse", "body": shift_hex(brief["primary_color"], -18), "accent": brief["accent_color"], "wheels": "#0f1218", "cabin": "#c7d2e2"},
        {"name": "Solar Echo", "body": shift_hex(brief["primary_color"], 18), "accent": shift_hex(brief["accent_color"], 20), "wheels": "#2b2f3e", "cabin": "#f4f1eb"},
    ]
    cleaned: list[dict[str, str]] = []
    for idx, item in enumerate(colorways[:3]):
        cleaned.append({
            "name": str(item.get("name", fallback[idx]["name"])).strip(),
            "body": normalize_hex(str(item.get("body", fallback[idx]["body"])).strip(), fallback[idx]["body"]),
            "accent": normalize_hex(str(item.get("accent", fallback[idx]["accent"])).strip(), fallback[idx]["accent"]),
            "wheels": normalize_hex(str(item.get("wheels", fallback[idx]["wheels"])).strip(), fallback[idx]["wheels"]),
            "cabin": normalize_hex(str(item.get("cabin", fallback[idx]["cabin"])).strip(), fallback[idx]["cabin"]),
        })
    while len(cleaned) < 3:
        cleaned.append(fallback[len(cleaned)])
    return cleaned


def normalize_hex(value: str, fallback: str) -> str:
    value = value if value.startswith("#") else f"#{value}"
    return value if re.fullmatch(r"#[0-9a-fA-F]{6}", value) else fallback


def shift_hex(hex_color: str, amount: int) -> str:
    hex_color = normalize_hex(hex_color, "#667eea")
    parts = [int(hex_color[i : i + 2], 16) for i in (1, 3, 5)]
    shifted = [max(0, min(255, p + amount)) for p in parts]
    return "#" + "".join(f"{p:02x}" for p in shifted)


def generate_local_concept(brief: dict[str, str]) -> dict[str, Any]:
    seed = int(hashlib.sha1(json.dumps(brief, sort_keys=True).encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    first = ["Nova", "Aero", "Volt", "Phantom", "Zenith", "Pulse", "Halo", "Rift"]
    second = ["GT", "Flux", "One", "Racer", "Drive", "Arc", "XR", "Vision"]
    name = f"{rng.choice(first)} {rng.choice(second)}"
    return {
        "name": name,
        "tagline": rng.choice([
            "Built for tomorrow's roads.",
            "Where concept meets velocity.",
            "Electric drama. Precision control.",
            "Designed to steal the skyline.",
        ]),
        "description": (
            f"{name} is a {brief['style'].lower()} concept shaped for {brief['occasion'].lower()} moments. "
            f"It pairs {brief['material'].lower()} surfaces with {brief['primary_color']} as the hero tone and "
            f"{brief['accent_color']} as the visual pulse. The whole build channels {brief['inspiration']} into a cinematic road presence."
        ),
        "materials": MATERIAL_NOTES.get(brief["material"], MATERIAL_NOTES["Mixed Performance"])[:3],
        "features": [
            f"{brief['style']} silhouette with active aero channels",
            f"{brief['occasion']} tuned suspension package",
            "Full-width reactive light blade",
            "Augmented HUD with route intelligence",
            f"Cabin accents inspired by {brief['inspiration']}",
        ],
        "powertrain": rng.choice([
            "Tri-motor electric vector drive",
            "Hydrogen-electric hybrid thrust system",
            "Dual-motor grand touring EV platform",
        ]),
        "cockpit_theme": rng.choice([
            "Wraparound holo-dash with floating controls",
            "Pilot-inspired cabin with layered ambient light",
            "Minimal glass cockpit with tactile drive spine",
        ]),
        "target_driver": rng.choice([
            "Trend-forward urban performance drivers",
            "Collectors chasing a cinematic concept feel",
            "Drivers who want tech presence with everyday usability",
        ]),
        "retail_price": PRICE_BANDS.get(brief["occasion"], "$120,000"),
        "style_tags": STYLE_TAGS.get(brief["style"], ["future-ready", "bold stance", "concept energy"]),
        "colorways": normalize_colorways([], brief),
    }


def build_image_url(concept: dict[str, Any], brief: dict[str, str]) -> str:
    prompt = (
        f"futuristic concept car studio render, {concept['name']}, {brief['style']} design, "
        f"{brief['material']} body details, primary {brief['primary_color']}, accent {brief['accent_color']}, "
        f"inspired by {brief['inspiration']}, front three quarter angle, premium automotive product photography, "
        f"clean background, ultra detailed"
    )
    return f"https://image.pollinations.ai/prompt/{quote_plus(prompt)}?width=1024&height=640&seed=7&model=flux"


if __name__ == "__main__":
    app.run(debug=True, port=5000)
