# TINGLE â€” Your Before-You-Tap Spider-Sense

TINGLE is a Streamlit prototype inspired by Spider-Man's Spider-Sense. It helps students pause before acting on a message that may ask them to pay, click a link, share a code, or install software.

## How it works

- In Live mode, the configured Anthropic model extracts claims, requested actions, evidence, URLs, and uncertainties from pasted text or a screenshot.
- Pydantic validates the model response.
- TINGLE's Python rulesâ€”not the modelâ€”choose `STOP & VERIFY`, `PAUSE & VERIFY`, or `NO STRONG WARNING SIGNALS FOUND`.
- The `inspect_url` tool parses URL text locally. It does not open or fetch links.
- The evidence web connects the claim, signals, requested action, evidence, and safer next step.

## Run on Windows

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Sample mode works without a key and uses synthetic examples. Live mode requires `ANTHROPIC_API_KEY` in a local `.env` file. Do not commit `.env` or share the key.

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Privacy and limitations

Live analysis sends the submitted text or screenshot to the configured model provider. Do not use real private or sensitive messages in a demo. TINGLE cannot prove a message is fraudulent or safe; â€œNo strong warning signals foundâ€ does not establish that a message is safe.

## Demo

Use the clearly labelled synthetic sample cases. Show a warning example and a benign comparison, then explain the evidence web, deterministic rules, and limitations.
