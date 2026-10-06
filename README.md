# AI Car Concept Lab[cite: 1]

A stylish three-page Flask app that turns a structured brief into a futuristic car concept.[cite: 1]

## Features[cite: 1]
- Home, Studio, and History pages[cite: 1]
- Structured product brief[cite: 1]
- Real AI text generation with Groq when `GROQ_API_KEY` is set[cite: 1]
- Clean local fallback concept generation when no key is set[cite: 1]
- Session-based concept history[cite: 1]
- Futuristic UI with live colorway cards and SVG concept render[cite: 1]
- External concept image via Pollinations image prompt URL[cite: 1]

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
- If you do not add a Groq key, the app still works using a polished local fallback generator.[cite: 1]
- History is stored in the browser session.[cite: 1]