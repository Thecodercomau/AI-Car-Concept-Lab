# AI Car Concept Lab

A three-page Flask product that turns a structured design brief into a complete futuristic car concept: name, positioning, materials, features, pricing, colorways, an AI studio render, and a live SVG colorway explorer. Every generated concept is saved to session history.

## Features

- **Home** — product overview and entry points into the workflow
- **Studio** — structured design brief with hCaptcha protection, AI concept generation, an AI studio render, and a live SVG colorway explorer
- **History** — every concept saved during the same browser session, with pricing, colorways, materials, features, and full specs
- Server-side session history (no cookie-size limit, so the whole session is retained)
- hCaptcha verification before any AI call
- Groq-backed server-side generation with a deterministic local fallback
- Optional per-request Hugging Face generation from the browser
- AI image render via Pollinations, proxied and cached by Flask, with a color-matched SVG fallback if the image service is rate-limited

## Folder Structure

```text
ai-car-concept-lab/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── studio.html
│   └── history.html
└── static/
    ├── css/
    │   └── styles.css
    ├── img/
    │   └── car-placeholder.svg
    └── js/
        └── studio.js
```

## Run

```bash
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

Open `http://127.0.0.1:5000`. If that port is already in use, start with `APP_PORT=5001 python app.py` and open `http://127.0.0.1:5001`.

## Environment

`config.py` loads `.env` automatically. Only the first two values are required for the full AI flow:

- `FLASK_SECRET_KEY` — signs the session cookie; set a long random value
- `GROQ_API_KEY` — server-side concept generation
- `GROQ_MODEL` — defaults to `openai/gpt-oss-120b`
- `HCAPTCHA_SITE_KEY` / `HCAPTCHA_SECRET_KEY` — enable hCaptcha when both are set (the secret also accepts `HCAPTCHA_SECRET`); leave both blank to disable it for local development
- `HF_API_KEY` — optional, reserved for Hugging Face server-side use
- `SESSION_FILE_DIR` — optional path for the server-side session store (defaults to `.flask_session/`)
- `APP_PORT` — optional local port (defaults to `5000`; a valid `PORT` from the host is also honored)

## How Generation Works

1. The Studio submits the brief to `/verify-captcha`. The server validates the hCaptcha token and marks the session as verified.
2. If the user supplied a Hugging Face access token, the browser generates the structured JSON concept directly with Hugging Face and posts it to `/generate`.
3. If the token is blank, `/generate` generates the concept server-side with Groq. If the provider is unavailable, the deterministic local concept engine keeps the studio usable.
4. The server sanitizes the concept, timestamps it, saves it to the session history, and points the concept at a local image route.
5. `/concept-image/<fingerprint>` fetches the Pollinations render, caches successful images in `.image_cache/`, and returns a color-matched SVG preview when the provider is rate-limited or unavailable.
6. The Studio renders the result and lets the user switch between all three colorways in the live SVG.

## Session History

History uses a server-side Flask-Session filesystem store. The browser only holds a signed session ID, so twelve or more detailed AI concepts do not overflow the browser's cookie limit. History includes every concept generated in the current browser session, newest first. **Clear History** removes them from that session. Restarting the browser starts a new session.

## Notes

- For AI-generated concepts, set `GROQ_API_KEY` or enter a Hugging Face token in the Studio. Without either, the deterministic local concept engine still produces a complete concept.
- Pollinations allows one free image request every 45 seconds per IP. When the limit is hit, the image route returns a color-matched SVG built from that concept's first colorway, so the Studio and History never show a provider error page. Successful renders are cached in `.image_cache/` (ignored by git).
- Run `python app.py` for development. `debug=True` is enabled in the `__main__` block only.
