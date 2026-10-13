"""
IT-ordboken - en enkel GenAI-app.
Användaren skriver ett IT-begrepp, Gemini förklarar det på enkel svenska.
API-nyckeln läses från miljövariabeln GEMINI_API_KEY och finns ALDRIG i koden.
"""

import os

import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Modeller i prioritetsordning: den snabba lite-modellen först,
# reserv om den är överbelastad eller saknas.
GEMINI_MODELS = os.environ.get(
    "GEMINI_MODELS", "gemini-flash-lite-latest,gemini-flash-latest"
).split(",")
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
TIMEOUT_PER_MODEL = 25  # sekunder
# Fel där det är värt att prova nästa modell
RETRY_STATUS = {404, 429, 500, 503, 504}

SYSTEM_PROMPT = (
    "Du är en pedagogisk IT-lärare. Förklara IT-begreppet som användaren skriver "
    "på enkel svenska, så att en nybörjare förstår. Svara kort: högst 6 meningar. "
    "Ge ett konkret exempel från vardagen eller från IT-drift. "
    "Om texten inte är ett IT-begrepp, säg det vänligt och be om ett IT-begrepp."
)

PAGE = """<!doctype html>
<html lang="sv">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IT-ordboken</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 640px; margin: 40px auto;
         padding: 0 16px; background: #f6f7f9; color: #1d2330; }
  h1 { margin-bottom: 4px; }
  p.sub { color: #5a6475; margin-top: 0; }
  form { display: flex; gap: 8px; margin: 24px 0; }
  input { flex: 1; padding: 12px; font-size: 16px; border: 1px solid #c8cdd6;
          border-radius: 8px; }
  button { padding: 12px 18px; font-size: 16px; border: 0; border-radius: 8px;
           background: #2456d6; color: #fff; cursor: pointer; }
  button:disabled { background: #8aa0d8; cursor: wait; }
  #svar { white-space: pre-wrap; background: #fff; padding: 16px;
          border-radius: 8px; min-height: 60px; border: 1px solid #e1e4ea; }
</style>
</head>
<body>
  <h1>IT-ordboken</h1>
  <p class="sub">Skriv ett IT-begrepp, så förklarar AI:n det på enkel svenska.</p>
  <form id="f">
    <input id="ord" placeholder="t.ex. DNS, VLAN, brandvägg" maxlength="100" required>
    <button id="knapp">Förklara</button>
  </form>
  <div id="svar"></div>
<script>
  const f = document.getElementById("f");
  const knapp = document.getElementById("knapp");
  const svar = document.getElementById("svar");
  f.addEventListener("submit", async (e) => {
    e.preventDefault();
    knapp.disabled = true;
    svar.textContent = "Tänker...";
    try {
      const r = await fetch("/api/forklara", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ord: document.getElementById("ord").value })
      });
      const data = await r.json();
      svar.textContent = data.svar || data.fel || "Något gick fel.";
    } catch (err) {
      svar.textContent = "Kunde inte nå servern.";
    }
    knapp.disabled = false;
  });
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return PAGE


@app.route("/api/forklara", methods=["POST"])
def forklara():
    ord_ = (request.get_json(silent=True) or {}).get("ord", "").strip()
    if not ord_ or len(ord_) > 100:
        return jsonify(fel="Skriv ett begrepp (max 100 tecken)."), 400

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return jsonify(fel="Servern saknar API-nyckel."), 500

    body = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": ord_}]}],
    }
    senaste_fel = "okänt fel"
    r = None
    for model in GEMINI_MODELS:
        model = model.strip()
        try:
            r = requests.post(
                f"{GEMINI_BASE}{model}:generateContent",
                headers={"x-goog-api-key": api_key.strip()},
                json=body,
                timeout=TIMEOUT_PER_MODEL,
            )
        except requests.RequestException as e:
            senaste_fel = f"{model}: {type(e).__name__}"
            app.logger.warning("Nätverksfel/timeout %s", senaste_fel)
            r = None
            continue

        if r.status_code == 200:
            break

        # Googles felmeddelande (innehåller aldrig nyckeln)
        try:
            msg = r.json().get("error", {}).get("message", "")
        except ValueError:
            msg = r.text[:200]
        senaste_fel = f"{model}: fel {r.status_code}: {msg}"
        app.logger.warning("Gemini %s", senaste_fel)
        if r.status_code not in RETRY_STATUS:
            break  # t.ex. ogiltig nyckel - ingen idé att försöka igen
        r = None

    if r is None or r.status_code != 200:
        return jsonify(fel=f"AI-tjänsten svarade inte ({senaste_fel}). Försök igen."), 502

    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    except (KeyError, IndexError, ValueError):
        app.logger.error("Oväntat svar från Gemini: %s", r.text[:300])
        return jsonify(fel="AI-tjänsten gav inget svar. Försök med ett annat ord."), 502
    return jsonify(svar=text.strip() or "Inget svar.")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
