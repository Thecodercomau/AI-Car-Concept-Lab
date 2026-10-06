from __future__ import annotations
 
import hashlib
import json
import os
import random
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus
 
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
 
load_dotenv()
 
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "ai-car-concept-lab-dev-key")
app.config["SESSION_PERMANENT"] = False
 
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_HISTORY = 12
 
 
STYLE_TAGS = {
    "Hypercar": ["aggressive aero", "track-ready stance", "dramatic lighting"],
    "Luxury": ["executive comfort", "clean surfacing", "premium cabin"],
    "Off-Road": ["raised ride height", "rugged utility", "all-terrain confidence"],
    "EV": ["clean tech aesthetic", "silent performance", "futuristic cockpit"],
    "Retro-Future": ["classic proportions", "neo-futurist detailing", "heritage remix"],
    "Street": ["urban stance", "after-dark energy", "custom performance"],
}
 
MATERIAL_NOTES = {
    "Carbon Fiber": ["carbon composite body panels", "forged aero fins", "lightweight frame"],
    "Aluminum": ["aluminum monocoque", "satin body surfaces", "precision-machined trim"],
    "Titanium": ["titanium highlights", "heat-blued accents", "ultra-premium shell"],
    "Recycled Composite": ["sustainable composite shell", "eco-performance interior", "recycled weave trim"],
    "Glass & Metal": ["panoramic glass canopy", "brushed alloy bodywork", "sculpted metallic spine"],
    "Mixed Performance": ["hybrid material shell", "performance mesh vents", "contrasting aero textures"],
}
 
PRICE_BANDS = {
    "Daily Drive": "$58,000",
    "Track Day": "$210,000",
    "Adventure": "$96,000",
    "Collector Reveal": "$320,000",
    "City Tech": "$74,000",
    "Luxury Tourer": "$168,000",
}
 
 
@app.route("/")
def index() -> str:
    return render_template("index.html")
 
 
@app.route("/studio")
def studio() -> str:
    return render_template("studio.html")
 
 
@app.route("/history")
def history() -> str:
    return render_template("history.html", designs=get_history())
 
 
@app.post("/api/generate")
def generate() -> Any:
    payload = request.get_json(silent=True) or {}
    brief = normalize_brief(payload)
    missing = [k for k, v in brief.items() if not v]
    if missing:
        return jsonify({"ok": False, "error": "Please complete all design brief fields."}), 400
 
    concept = generate_concept(brief)
    image_url = build_image_url(concept, brief)
    concept["image_url"] = image_url
    concept["brief"] = brief
    concept["timestamp"] = datetime.now().strftime("%d %b %Y, %I:%M %p")
    concept["fingerprint"] = fingerprint(brief, concept["name"])
 
    add_to_history(concept)
    return jsonify({"ok": True, "concept": concept})
 
 
@app.post("/clear-history")
def clear_history() -> Any:
    session["designs"] = []
    return jsonify({"ok": True})
 
 
def normalize_brief(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "style": str(payload.get("style", "")).strip(),
        "material": str(payload.get("material", "")).strip(),
        "occasion": str(payload.get("occasion", "")).strip(),
        "primary_color": str(payload.get("primary_color", "")).strip(),
        "accent_color": str(payload.get("accent_color", "")).strip(),
        "inspiration": str(payload.get("inspiration", "")).strip(),
    }
 
 
def get_history() -> list[dict[str, Any]]:
    return session.get("designs", [])
 
 
def add_to_history(concept: dict[str, Any]) -> None:
    current = session.get("designs", [])
    deduped = [d for d in current if d.get("fingerprint") != concept["fingerprint"]]
    session["designs"] = [concept] + deduped[: MAX_HISTORY - 1]
    session.modified = True
 
 
def fingerprint(brief: dict[str, str], name: str) -> str:
    raw = "|".join([brief["style"], brief["material"], brief["occasion"], brief["primary_color"], brief["accent_color"], brief["inspiration"], name])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:14]
 
 
def generate_concept(brief: dict[str, str]) -> dict[str, Any]:
    if GROQ_API_KEY:
        concept = generate_via_groq(brief)
        if concept:
            return concept
    return generate_local_concept(brief)
 
 
def generate_via_groq(brief: dict[str, str]) -> dict[str, Any] | None:
    system_prompt = (
        "You are a senior futuristic car concept designer. "
        "Return ONLY valid JSON. No markdown, no explanation."
    )
    user_prompt = f'''
Create one futuristic car concept from this structured brief.
 
Brief:
- Style: {brief['style']}
- Material: {brief['material']}
- Occasion: {brief['occasion']}
- Primary colour: {brief['primary_color']}
- Accent colour: {brief['accent_color']}
- Inspiration: {brief['inspiration']}
 
Return JSON with exactly these keys:
name, tagline, description, materials, features, powertrain, cockpit_theme,
target_driver, retail_price, style_tags, colorways
 
Rules:
- materials: array of 3 to 5 strings
- features: array of 4 to 6 strings
- style_tags: array of 3 short strings
- colorways: array of exactly 3 objects
- each colorway object must contain: name, body, accent, wheels, cabin
- keep retail_price as a string like "$120,000"
- make the result vivid, premium, and product-like
'''
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.9,
            },
            timeout=45,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip()
        match = re.search(r"\{[\s\S]*\}", content)
        if not match:
            return None
        concept = json.loads(match.group(0))
        if not is_valid_concept(concept):
            return None
        return sanitize_concept(concept, brief)
    except Exception:
        return None
 
 
def is_valid_concept(concept: dict[str, Any]) -> bool:
    required = [
        "name",
        "tagline",
        "description",
        "materials",
        "features",
        "powertrain",
        "cockpit_theme",
        "target_driver",
        "retail_price",
        "style_tags",
        "colorways",
    ]
    return all(k in concept for k in required) and isinstance(concept.get("colorways"), list)
 
 
def sanitize_concept(concept: dict[str, Any], brief: dict[str, str]) -> dict[str, Any]:
    clean = {
        "name": str(concept.get("name", "Concept X")).strip(),
        "tagline": str(concept.get("tagline", "Future in motion.")).strip(),
        "description": str(concept.get("description", "")).strip(),
        "materials": [str(x).strip() for x in concept.get("materials", [])][:5] or MATERIAL_NOTES.get(brief["material"], [])[:3],
        "features": [str(x).strip() for x in concept.get("features", [])][:6] or ["Adaptive aero body", "Panoramic digital cockpit", "Active rear light blade", "Performance-tuned handling"],
        "powertrain": str(concept.get("powertrain", "Quad-motor electric performance")).strip(),
        "cockpit_theme": str(concept.get("cockpit_theme", "Minimal driver-first cockpit")).strip(),
        "target_driver": str(concept.get("target_driver", "Design-forward performance enthusiasts")).strip(),
        "retail_price": str(concept.get("retail_price", PRICE_BANDS.get(brief["occasion"], "$120,000"))).strip(),
        "style_tags": [str(x).strip() for x in concept.get("style_tags", [])][:3] or STYLE_TAGS.get(brief["style"], [])[:3],
        "colorways": normalize_colorways(concept.get("colorways", []), brief),
    }
    return clean
 
 
def normalize_colorways(colorways: list[dict[str, Any]], brief: dict[str, str]) -> list[dict[str, str]]:
    fallback = [
        {
            "name": "Launch Spec",
            "body": brief["primary_color"],
            "accent": brief["accent_color"],
            "wheels": "#1b1e28",
            "cabin": "#d9dce5",
        },
        {
            "name": "Midnight Signal",
            "body": shift_hex(brief["primary_color"], -18),
            "accent": brief["accent_color"],
            "wheels": "#0f1218",
            "cabin": "#c7d2e2",
        },
        {
            "name": "Volt Mirage",
            "body": shift_hex(brief["primary_color"], 18),
            "accent": shift_hex(brief["accent_color"], 20),
            "wheels": "#2b2f3e",
            "cabin": "#f4f1eb",
        },
    ]
    cleaned: list[dict[str, str]] = []
    for idx, item in enumerate(colorways[:3]):
        cleaned.append(
            {
                "name": str(item.get("name", fallback[idx]["name"])).strip(),
                "body": normalize_hex(str(item.get("body", fallback[idx]["body"])).strip(), fallback[idx]["body"]),
                "accent": normalize_hex(str(item.get("accent", fallback[idx]["accent"])).strip(), fallback[idx]["accent"]),
                "wheels": normalize_hex(str(item.get("wheels", fallback[idx]["wheels"])).strip(), fallback[idx]["wheels"]),
                "cabin": normalize_hex(str(item.get("cabin", fallback[idx]["cabin"])).strip(), fallback[idx]["cabin"]),
            }
        )
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
    taglines = [
        "Built for tomorrow's roads.",
        "Where concept meets velocity.",
        "Electric drama. Precision control.",
        "Designed to steal the skyline.",
    ]
    materials = MATERIAL_NOTES.get(brief["material"], MATERIAL_NOTES["Mixed Performance"])
    features = [
        f"{brief['style']} silhouette with active aero channels",
        f"{brief['occasion']} tuned suspension package",
        "Full-width reactive light blade",
        "Augmented HUD with route intelligence",
        f"Cabin accents inspired by {brief['inspiration']}",
    ]
    description = (
        f"{name} is a {brief['style'].lower()} future concept shaped for {brief['occasion'].lower()} moments. "
        f"It pairs a {brief['material'].lower()}-driven body language with {brief['primary_color']} as the hero tone and "
        f"{brief['accent_color']} as the electric punch. The entire build channels {brief['inspiration']} into a sleek, cinematic road presence."
    )
    return {
        "name": name,
        "tagline": rng.choice(taglines),
        "description": description,
        "materials": materials[:3],
        "features": features[:5],
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
