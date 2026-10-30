# 🕷️ TINGLE
### Your Before-You-Tap Spider-Sense

![Python](https://img.shields.io/badge/Built%20with-Python-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)
![Sample mode](https://img.shields.io/badge/Sample%20mode-Offline-2E8B57)

**TINGLE helps students pause and verify before acting on a suspicious or pressuring digital message.** Inspired by Spider-Man’s Spider-Sense, it connects what a message claims, what it asks someone to do, and the evidence supporting a cautious next step.

> ⚠️ **TINGLE is a verification aid, not a scam detector or safety guarantee.** “No strong warning signals found” does **not** prove a message is safe.

---

## 🎯 The problem

Messages can pressure students to pay a fee, click a link, share a one-time code, or install software. When a message feels urgent, it can be difficult to pause and evaluate its claims.

## 💡 The solution

TINGLE lets a user paste message text or submit a screenshot. It presents relevant claims, requested actions, warning signals, evidence, and a safer next step.

TINGLE **does not** click links, make payments, block messages, or report anyone on the user’s behalf.

---

## ⚙️ How it works

1. **Input:** The user pastes text or uploads an image.
2. **Structured extraction:** In optional Live mode, the model extracts claims, requested actions, evidence, URLs, and uncertainties.
3. **Validation:** Pydantic validates the structured response.
4. **Decision:** Local Python rules—not the model—choose the warning level.
5. **Evidence:** The interface shows how the claim, signals, requested action, and evidence connect.

TINGLE can show one of these outcomes:

- 🛑 **STOP & VERIFY**
- ⚠️ **PAUSE & VERIFY**
- ✅ **NO STRONG WARNING SIGNALS FOUND**

The last outcome is **not** proof that the message is safe.

---

## 🧠 GenAI and API usage

This repository contains an **optional Anthropic-backed Live analysis path** in `core/model_client.py`.

| Mode | API key needed? | Makes an AI-provider call? |
|---|---:|---:|
| **Sample mode** | No | **No** — uses synthetic examples |
| **Live mode** | Yes | **Yes** — uses the configured Anthropic integration |

**The current sample-mode demo is offline and does not call Anthropic.** Live mode requires an `ANTHROPIC_API_KEY` in a local `.env` file. No API key is included in this repository.

---

## 🕸️ What makes TINGLE different?

- **Evidence-first:** The interface connects signals to evidence and a practical next step.
- **Model plus rules:** The optional model extracts information; deterministic Python rules make the final risk decision.
- **Validated output:** Pydantic checks the model’s structured response.
- **Careful URL handling:** `tools/inspect_url.py` parses URL text locally. It does **not** open or fetch the link.
- **Multimodal Live path:** The code supports text and image input when Live mode is configured.
- **Spider-Man-inspired experience:** The Spider-Sense theme makes “pause and verify” the core interaction.

---

## 🚀 Run locally on Windows

Open PowerShell in the project folder and run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Without an API key, use **sample mode** and its synthetic examples.


---

## 🧪 Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

---

## 🔐 Privacy and limitations

- In **sample mode**, TINGLE uses synthetic examples and makes no AI-provider call.
- In **Live mode**, submitted text or images are sent to the configured provider for analysis.
- Do not submit personal, confidential, or sensitive content.
- Never store an API key in GitHub. Keep `.env` local.
- TINGLE cannot prove who sent a message or determine with certainty that it is fraudulent or safe.
- HTTPS or a lack of warning signals does not prove that a website or message is trustworthy.

---

## 📁 Project structure

```text
app.py                 Streamlit application
core/                  Extraction pipeline, schemas, and risk rules
tools/                 Constrained URL-text inspection
ui/                    Evidence web and interface styling
examples/               Synthetic sample cases
tests/                  Automated tests
```
