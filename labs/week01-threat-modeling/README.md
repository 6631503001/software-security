# Week 1 — Security Mindset & Threat Modeling

**OWASP 2025:** A06 Insecure Design · **CWE focus:** CWE-501 (Trust Boundary Violation)

## ✅ This week — what to do
1. **Before class** — **Set up your environment** — install **Docker Desktop** + Burp/ZAP (a Linux VM is an optional fallback). This *is* **Lab 0**.
2. **Slides, then class** — read `slides/week01.md` and answer the worksheet's **Part 2** before class; class opens with the weekly quiz (~10 min) and a short explanation + demo (~15 min).
3. **Lab (in class)** — play this week's game, then complete **Worksheet 1** (`worksheet.md`, Parts 1–4, incl. *Audit the AI* + *EiPE/Prompt*). Kickoff: `docker compose up` → `http://localhost:8080/notes` (the bare `/` is a 404 by design — see Task 0). Part 3 marks each task *in class* or *homework*.
4. **Submit before the next class** (homework tasks included) — worksheet PDF → `learn.zcr.ai/submit` · code → GitHub · weekly quiz → `learn.zcr.ai/quiz`. (How: [SUBMISSION.md](../../SUBMISSION.md).)
5. **Project** — apply this week's lesson to your [NoteVault project](../../project/README.md) where it fits.

*Time breakdown: [AGENDA.md](../../AGENDA.md). Grading: see the worksheet rubric.*

## Objectives
- Explain the CIA triad, trust boundaries, and attack surface.
- Build a data-flow diagram (DFD) and apply STRIDE to a real app.
- Navigate the OWASP Top 10, MITRE CWE, and ATT&CK.
- Frame the course with **"Secure by Design"** (CISA) and the industry shift to memory-safe languages.

## 🎲 Signature game — "Elevation of Privilege"
Play Microsoft's free STRIDE threat-modeling card deck against the sample app's DFD — each valid threat scores a point. Get the deck (print-and-play PDF, free, Creative Commons): [github.com/adamshostack/eop](https://github.com/adamshostack/eop). No printer? Worksheet Task 3 embeds a digital deck — same 78 cards, playable in-browser.

## Lab 0 — Environment setup (do once)
1. Install **Docker Desktop** (macOS/Windows) or Docker Engine + Compose (Linux). On Windows also install **Git for Windows** and run the course's commands in **Git Bash** (or WSL), not PowerShell or cmd.
2. Install a browser proxy: Burp Suite Community **or** OWASP ZAP.
3. Verify: `docker run hello-world` and `git --version`.
4. *Fallback only, if Docker will not run on your machine* — install VirtualBox/UTM with a Kali or Ubuntu VM and put Docker inside it. Every later unit states its prerequisite as Docker working from Lab 0, so this is the exception, not the normal path. The labs listen on the VM's own `localhost` only (so nobody else on the network can reach them), which means you open them in a browser *inside* the VM.

## Lab 1 — Threat-model a sample app
You are given a small web app (source provided by instructor).
1. Draw a DFD: processes, data stores, external entities, and trust boundaries.
2. For each element, enumerate **S**poofing, **T**ampering, **R**epudiation, **I**nfo disclosure, **D**oS, **E**levation.
3. Rank the top 5 threats by likelihood × impact.
4. Propose one mitigation per top threat.

## Deliverable
A 2–3 page threat model (DFD image + STRIDE table + top-5 risk ranking).

## References
- https://owasp.org/Top10/2025/
- https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html
