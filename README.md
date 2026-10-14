# AI Car Concept Lab[cite: 1]

A stylish three-page Flask app that turns a structured brief into a futuristic car concept.[cite: 1]

## Features[cite: 1]
- Home, Studio, and History pages[cite: 1]
- Structured product brief[cite: 1]
- Hugging Face Inference Providers text generation from the Studio using a per-request access token[cite: 1]
- Groq-backed generation or a local fallback for server-side API requests[cite: 1]
- Session-based concept history[cite: 1]
- Futuristic UI with live colorway cards and SVG concept render[cite: 1]
- External concept image via Pollinations image prompt URL[cite: 1]
- Optional hCaptcha protection for concept generation[cite: 1]

## Folder Structure[cite: 1]
```text
ai-car-concept-lab/
├── app.py
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
    │   └── style.css
    └── js/
        └── studio.js
```[cite: 1]

## Run[cite: 1]
```bash
pip install -r requirements.txt
cp .env.example .env
python app.py
```[cite: 1]

Then open `http://127.0.0.1:5000`.[cite: 1]

## Notes[cite: 1]
- The Studio requires a Hugging Face token; server-side `/generate` callers can use Groq when configured or the local fallback otherwise.[cite: 1]
- In the Studio, provide a Hugging Face access token with permission to call Inference Providers. The browser sends the token directly to Hugging Face for that request; it is not stored or sent to the Flask app. The Studio uses `Qwen/Qwen2.5-7B-Instruct` by default.[cite: 1]
- To enable hCaptcha, set both `HCAPTCHA_SITE_KEY` and `HCAPTCHA_SECRET_KEY`; generation requests are verified server-side. Leave both unset to disable CAPTCHA for local development.[cite: 1]
- History is stored in the browser session.[cite: 1]