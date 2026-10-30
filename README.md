🕷️ TINGLE — Your Before-You-Tap Spider-Sense
Project Spider-Sense · GenAI prototype

TINGLE helps students pause before acting on a suspicious or pressuring digital message. It connects what a message claims, what it asks the reader to do, and the evidence that supports a cautious next step.

TINGLE is a verification aid, not a scam oracle. “No strong warning signals found” does not prove that a message is safe.

🎯 The problem and solution
Students can receive messages that pressure them to pay a fee, click a link, share a one-time code, or install software. TINGLE lets a user paste text or submit a PNG/JPG screenshot, then presents evidence and practical verification advice before the user acts.

The Spider-Man theme is part of the workflow: Spider-Sense is the warning before action, while the evidence web connects the claim, signals, requested action, evidence, and safer next step. TINGLE never clicks, pays, blocks, or reports anything for the user.

⚙️ How TINGLE works
The user pastes message text or uploads a screenshot.
The model integration requests an extraction of the claim, requested action, signals, quotes, URLs, and uncertainties. The submitted message is treated as untrusted data.
Pydantic validates the response. The app—not the model—applies the deterministic rules in core/risk_rules.py.
If requested, tools/inspect_url.py parses a bounded HTTP/HTTPS URL locally. It does not open the link, fetch it, follow redirects, or make a network request.
The UI displays STOP & VERIFY, PAUSE & VERIFY, or NO STRONG WARNING SIGNALS FOUND, with the evidence web and a safer next step.
The extraction model does not produce a scam probability or decide the final warning state. A request to share an OTP/password or install remote-access software can trigger STOP & VERIFY; combinations such as a pressured payment can trigger PAUSE & VERIFY. A deadline alone is not enough for the strongest warning.

🧠 GenAI and the current demo setup
This repository contains an Anthropic-backed Live analysis path in core/model_client.py. Live mode requires ANTHROPIC_API_KEY in a local .env file. No API key is included in this repository.

The synthetic sample mode works without an API key and does not contact an AI provider. If the demo is run without a configured key, its sample output is hand-written—not a live GenAI result. Do not describe a sample-mode run as a live model call.

The Live path supports text and image input, structured extraction, and a constrained native inspect_url tool call. Use Live mode only if you already have authorized API access and understand the provider's usage terms and possible costs. The project does not enable billing or provide free API access.

🚀 Run locally on Windows
From the project folder:

PowerShell

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
Without ANTHROPIC_API_KEY, TINGLE opens in sample mode. For optional Live mode, use a local .env based on .env.example; never commit .env or share the key.

Run the tests:

PowerShell

.\.venv\Scripts\python.exe -m pytest -q
Report the test result you actually get on the submitted version; this README does not claim a test count.

🧪 Demo suggestion
Use only the synthetic cases in examples/sample_cases.json:

Show a sample that asks for an urgent fee and explain the evidence leading to PAUSE & VERIFY.
Show a benign deadline-only message and explain why a deadline alone is not treated as the strongest warning.
Show the evidence web and explain that a URL observation is not a verdict and the link is never opened.
Label sample output clearly as synthetic and offline. Do not submit real private messages or screenshots.

🛡️ Privacy, safety, and limitations
Live analysis sends the submitted text or screenshot to the configured model provider. Provider terms apply; avoid personal, sensitive, confidential, or identifying content.
Sample mode uses synthetic data locally and does not make a provider call.
API credentials belong only in a local .env, which is ignored by Git. Never commit secrets.
TINGLE is not a live threat-intelligence service. It cannot verify who sent a message, prove fraud, or prove safety.
The URL tool only inspects URL text; HTTPS alone is not proof that a site is safe.
