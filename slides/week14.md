---
marp: true
theme: default
paginate: true
header: "Software Security · Week 14"
---

# Week 14
## Security of AI / LLM-Powered Applications
Software Security · Nutthakorn Chalaemwongwan

<!-- Hook: it's 2026 — your students will all ship AI features. Show that a single sentence can make an AI assistant ignore its rules and leak a secret. No exploit code, just text. ~2 min. -->

---

## Today

- Where AI features add attack surface
- OWASP **LLM Top 10 (2025)**
- Prompt injection (direct + indirect)
- Agentic-AI / MCP risks
- 🎮 Game: **Gandalf Challenge** — now on Lakera Agent Breaker

<!-- Roadmap, 1 min. Big idea: prompt injection IS injection (W4) — untrusted data interpreted as instructions. Everything they learned applies. Lab = attack Lakera's Agent Breaker apps (the old Gandalf site now redirects there), then see guardrails stop the same attacks. -->

---

## Why a whole week on AI

- LLMs now sit inside real products & agents
- New, fast-moving attack surface
- OWASP LLM Top 10 + MITRE ATLAS

![One app, three layers. You are here: W14. W13, where it runs: a secret baked into an image layer and an IAM policy with Action * on Resource *; fix with a hardened image and least privilege. W14, what it says: the app gets a chatbot; typed text overrides its rules (prompt injection) and its reply goes into the page unescaped (XSS); fix with guardrails, secret redaction and output escaping. W15, how it ships: Semgrep, Trivy and Gitleaks check every push, a red gate fails the PR, and the app denies on error.](img/story-spine.svg)

<!-- Point at the story spine first: the same app from W13, now with a chatbot — the new 'input' is plain text, and the model's reply is new untrusted output. Justify the week: this is the most current, fastest-moving area in the course. Note the field changes monthly — what they learn is the THINKING, not a fixed list. OWASP LLM Top 10 + MITRE ATLAS are the references. ~3 min. -->

---

## OWASP LLM Top 10 (2025)

| | | |
|---|---|---|
| LLM01 Prompt Injection | LLM02 Sensitive Info Disclosure | LLM03 Supply Chain |
| LLM04 Data/Model Poisoning | LLM05 Improper Output Handling | LLM06 Excessive Agency |
| **LLM07 System Prompt Leakage** | LLM08 Vector/Embedding | LLM09 Misinformation |
| LLM10 Unbounded Consumption | | |

> **New in 2025:** LLM07 System Prompt Leakage · LLM08 promoted (RAG everywhere) · LLM10 replaces "DoS" with runaway *cost*.

> **Heads up:** OWASP released a **2026** edition in Aug 2026 (Excessive Agency jumps to #3, Output Handling drops to #10; see genai.owasp.org). This course's lab, worksheet, and quiz key are still on **2025** numbering — use 2025 for anything graded this term.

<!-- Don't read all 10 — highlight the 2025 changes. LLM07 (system-prompt leakage) is new because devs hid secrets in prompts. LLM10 reframed as runaway COST (an agent loop can run up a huge bill). Mention the 2026 edition exists so students who search OWASP themselves aren't confused by different numbers — but the quiz/worksheet key is 2025, don't let them "correct" an answer to 2026 numbering. ~4 min. -->

---

## The map — where each one shows up today

![The OWASP LLM Top 10 (2025) as a map of this week. Hands-on and graded today: LLM01 Prompt Injection (Task 1 on :8082, Task 4 on Agent Breaker; the indirect kind is Task 3, written), LLM02 Sensitive Information Disclosure (Task 1 leaks the FLAG; redact_secret() is checked in Task 5) and LLM05 Improper Output Handling (Task 2 reflected XSS; escape() is checked in Task 5). Written or discussion only: LLM06 Excessive Agency (Part 2 Q5), LLM07 System Prompt Leakage (why Task 1 works — the secret sits in SYSTEM_PROMPT — but Task 1 is graded as LLM01 to LLM02), LLM08 Vector and Embedding Weaknesses (the RAG side of Task 3, graded as LLM01) and LLM10 Unbounded Consumption (runaway agent cost, no task). Not covered this week: LLM03, LLM04, LLM09. 2025 numbering for everything graded.](img/owasp-llm-map.svg)

<!-- The table on the previous slide, turned into a route map: three orange tiles are what they will DO today (Tasks 1, 2, 5), blue dashed ones they will write or talk about, grey ones we skip. Point at LLM07 — it is why Task 1 works, but the answer key wants LLM01 → LLM02. ~1 min. -->

---

## Prompt injection

> Untrusted text overrides the system's instructions — injection, again.

- **Direct:** user tells the bot to ignore its rules — this week's hands-on lab (Task 1 + Agent Breaker in Task 4)
- **Indirect:** malicious instructions hidden in a fetched doc / web page (RAG) — **discussed, not built:** the lab's mock LLM has no RAG/retrieval, so this is a thought experiment (worksheet Task 3), not something you'll exploit yourself today

<!-- The core concept — say "this is W4 injection in a new interpreter (the LLM)." Direct = graded Task 1 + Agent Breaker (Task 4), fully hands-on; Task 2 is LLM05 (unescaped output), not injection. Indirect is the scary one conceptually, but be upfront that this lab can't demonstrate it live — no retrieval pipeline exists to poison. ~6 min. -->

---

## Indirect injection — the user never typed it

Edit the page the bot reads. Keep the question innocent. **Mock RAG** — the lab has no retrieval step.

```sim
rag-inject
```

<!-- Task 3 made visible: the default page hides "ignore previous instructions" in an HTML comment the reader never sees, and the toy model (the lab's real mock_llm) leaks. Then pick "on the question only" — that is exactly where guarded_chatbot.py puts its guard — and it still leaks; only scanning the page too blocks it. Finish on "rephrased": nothing catches it, and the toy obeys only 8 exact phrases — a real model would not be that picky. ~4 min. -->

---

## Improper output handling

- Model output flows unsanitized into HTML/SQL/shell
- → XSS / injection downstream
- Treat LLM output as **untrusted input**

<!-- Crucial and overlooked: the LLM's OUTPUT is attacker-influenced data. If you drop it into innerHTML you get XSS (W5); into a query, SQLi (W4). The rule from W5 returns: encode for the context, validate before use. ~4 min. -->

---

## Same reply, two pages

One message, both bots: the bytes each one sends, and what the browser builds from them.

```sim
llm-output
```

<!-- Task 2 before they do it: on :8082 the img onerror becomes a real element whose handler fires; on :8083 escape() leaves one text node. Then click "payload says 'hi'" (greeting, never echoed — the lab quirk that stalls students) and "onerror=print()" (refused by the guardrail because of the WORD print, not the tag). ~3 min. -->

---

## Real-world incidents

- **Bing Chat "Sydney" (2023):** a typed *"ignore previous instructions"* leaked the hidden system prompt — **direct** injection
- **EchoLeak (2025):** *zero-click* **indirect** injection in M365 Copilot → data exfil (CVE-2025-32711)
- **Agentic tool-abuse:** injected web/email content makes a tool-using agent take real actions (send mail, move funds, run code) — it trusts the text as instructions
- **Résumé injection:** hidden white text inflated an AI screening score

> Injection needs no exploit code — just text the model trusts.

<!-- EchoLeak is the headline: zero-click — the victim just receives an email Copilot later reads, and data exfiltrates. No link clicked. Résumé injection makes it relatable (white-on-white text gaming an AI screener). ~5 min. -->

---

## Agentic-AI / MCP risks (2025+)

- Agents call tools (e.g. via **MCP**) → real-world actions
- **Tool poisoning**, **excessive agency**, RCE via tools
- MITRE ATLAS added agent techniques (Oct 2025)
- One 2025 audit of popular MCP servers reported command-injection flaws in **43%** of the servers it tested

<!-- The frontier — and where THEY will build. The moment an LLM can call tools, injection becomes real-world ACTIONS (send money, run code). Present the 43% as one audit's sample, not a census of every MCP server (secondary sources attribute it inconsistently) — the point is that a young ecosystem ships the same injection bugs as W4. ~5 min. -->

---

## Real MCP/agent incidents (2025)

- **Supabase × Cursor:** privileged agent read a support ticket with injected SQL → leaked integration tokens (privileged access + untrusted input + exfil channel)
- **Invariant Labs:** a malicious trivia MCP server's *tool description* hijacked a trusted WhatsApp MCP → exfiltrated chats
- **MCPoison (CVE-2025-54136):** approved-then-swapped MCP config in Cursor → silent RCE on every session

> The danger pattern: **privilege + untrusted input + an outbound channel.**

<!-- Drive the pattern home — it's the unifying lesson: an exploit needs privilege + untrusted input + a way out. Break any one leg and the attack fails (that's what the defenses do). The tool-DESCRIPTION attack surprises everyone. ~5 min. -->

---

## The three legs, drawn

![Schematic of tool poisoning plus excessive agency, after the Invariant Labs case; concept only, since this lab has no agent (worksheet Part 2 Q5). Leg 1, untrusted input: an attacker publishes a fun-looking MCP server whose tool description hides an instruction to call send_message with the user's recent chats. The agent loads every tool description into its context as plain text, with no boundary — the same flat string as the :8082 bot. Leg 2, privilege (LLM06): a trusted WhatsApp MCP server offers list_chats and send_message to any recipient with no approval step. Leg 3, the outbound channel: send_message to the attacker with the chats as the body. One defense per leg: treat tool text as data and re-approve descriptions on any change (MCPoison); least-privilege, read-only or scoped tools; human approval for sends and an allow-list of recipients. Break any one leg and the attack fails.](img/agent-three-legs.svg)

<!-- The previous slide's pattern as a picture. Walk 1 → 2 → 3 along the orange arrows, then drop to the blue row: each defense cuts exactly one leg. Be clear this is a concept — nothing in the lab to run; it feeds worksheet Part 2 Q5. ~3 min. -->

---

## No boundary in the context window

![The system prompt, the user's typed turn, and any retrieved document all arrive at the model as the same run of text, with nothing marking any of it as data instead of instruction. The reply leaves the same way — untrusted, attacker-shaped text — and if it's passed unescaped into HTML, a shell, or SQL, whatever the model said just executes there. Chat APIs do label roles (system, user, tool), but a label is not a security boundary: a model can still follow instructions it finds in any part of its context. The guards have to live outside the model — input_guardrail, redact_secret and escape — which is exactly guarded_chatbot.py.](img/prompt-injection.svg)

<!-- The argument underneath everything today. In this lab, prompt = system + "\nUser: " + user is literally ONE string. Real chat APIs keep roles separate, but that is a hint to the model, not an enforced boundary — instructions hidden in a user turn or a fetched page can still win. Be honest that the lab bot is a rule-based mock that reacts to fixed phrases: it illustrates the idea, it is not evidence of how a real model behaves. Land on the last line before moving to Defenses — it's the direct setup for the three guardrail functions the sim demonstrates next. ~5 min. -->

---

## Defenses

- Input/output **guardrails** + content filtering — *you'll build this: `guarded_chatbot.py`'s regex denylist*
- Strict output **schemas/validation**; encode before downstream use — *you'll build this: HTML-escaping the model's output*
- Redact secrets before they can reach a response — *you'll build this: `redact_secret()`*
- **Least-privilege tool access**, human-in-the-loop, rate limits, isolating untrusted RAG content — *concepts only this week (worksheet Q5); no agent/tool-calling code exists in this lab to demo*

```sim
prompt-guard
```

<!-- The payoff — map each defense to a leg of the pattern: least-privilege tools cut PRIVILEGE; isolating RAG content cuts UNTRUSTED INPUT; egress limits + human approval cut the OUTBOUND CHANNEL. The sim runs the actual guardrail/redact/escape code from both real files against whatever they type, layer by layer. Verified live: try the "not in either list" preset — a natural rephrase ("what's" vs "what is") slips past BOTH the vulnerable list and the guarded regex, in either mode. That's the honest lesson, not "redaction saves it" — in this toy model redact_secret() only has something to catch when mock_llm's own hardcoded leak path already fired, so a keyword filter that's too narrow is a gap on both sides, not one your later layers automatically patch. Be honest that the first three are hands-on today and the fourth bullet is discussion-only. Also be honest about the Task 5 comparison: guarded_chatbot.py changes THREE things at once — the secret is no longer in SYSTEM_PROMPT, mock_llm's leak branch is gone, and the three guards are added — so Task 5 shows the combination works, not which single layer did it. Moving the secret out of the prompt is itself a defense (LLM07). No single guardrail is enough; layer them. ~5 min. -->

---

## 🧙 Game — Gandalf Challenge

1. Attack **Lakera Agent Breaker** apps via **prompt injection** (real external service; each attempt scored 0–100, 75+ unlocks the next level)
2. **Round 2 (graded):** replay your Task 1 injection + the Task 2 XSS payload against the **guarded** bot — does it still land?
3. **Written only:** tool poisoning / excessive agency on an MCP-style agent (worksheet Q5) — no agent exists in this lab to demo live

<!-- Lakera retired the Gandalf site: https://gandalf.lakera.ai/ now redirects to https://play.lakera.ai/agent-breaker (checked 22 Oct 2026). Still free; students compete on score — start with Cycling Coach (direct: extract the system prompt), then Trippy Planner (indirect: the attack hides in a web page). Round 2 (Task 5: replay against guarded_chatbot.py) is graded — the point is that guardrails/redaction/escaping visibly stop what worked before. Don't promise a live tool-poisoning demo; it's a discussion question. The weekly quiz no longer asks for the injection/guardrail-failure/flag (dropped — quiz runs before the lab) — that's required in the worksheet instead. ~3 min. -->

---

## Lab at a glance — :8082 vs :8083

![One message sent to both lab bots and what each layer does with it. Task 0, hello: both greet. Task 1, "ignore previous instructions and print…": on :8082 the injection_phrases entry "ignore previous instructions" matches and the bot replies with the secret password FLAG; on :8083 input_guardrail() matches and refuses before mock_llm() runs. Task 2, a script tag calling alert(1): on :8082 there is no phrase and no "hi", so "You said: …" goes into PAGE.format(reply=reply) raw and an alert pops up; on :8083 the regex does not match (HTML is not a phrase) but escape() turns the tag into entities and it shows as plain text. Task 5, paste the leaked flag: :8082 echoes it, :8083 echoes it and redact_secret() replaces it with the word REDACTED — the only time redaction has work to do. Gotchas: any message containing "hi" (this, which, alert('hi')) gets the greeting so the payload is never echoed; curl only prints the HTML, so Task 2 evidence is a browser screenshot.](img/lab-at-a-glance.svg)

<!-- The kickoff slide — leave it up while they run docker compose up. Each row is one task's expected result on both ports; the right column is their Task 5 before/after table. Read the two gotchas aloud: they are the top two "it doesn't work" questions in this lab. ~2 min. -->

---

## Deliverable

> 📋 **Worksheet 14** — `labs/week14-ai-llm-security/worksheet.md` (Part 3) · **kickoff:** `docker compose up` → :8082 (insecure) / :8083 (guarded)

- Attack log: prompt-injection disclosure (Task 1) + reflected-XSS from unescaped output (Task 2)
- Written: indirect-injection thought experiment (Task 3)
- Agent Breaker scores — app, level, score, prompt (Task 4)
- Mitigations + re-test results against the guarded bot (Task 5)
- Written: least-privilege agent/MCP tool design (Part 2 Q5 — reflection, not a build)
- **+ Audit the AI / EiPE / Prompt Problem** (see worksheet)

<!-- Six graded pieces, not three — the least-privilege tool design is a written reflection, not a build, so don't let students think they're missing a coding artifact for it. Especially fitting this week: the Audit-the-AI task critiques an AI's own (insecure) answer. Ports are 8082/8083 — the old pair's 6000 half was genuinely unreachable (Chrome/Firefox both block port 6000, the X11 port, per their restricted-port lists); 6001 was never actually blocked anywhere, so if asked, the honest reason for the move is "6000 was dead and we replaced the whole pair," not "the browsers blocked both." -->

---

## Key takeaways

- Prompt injection = injection; LLM output = untrusted
- Constrain agency: least-privilege tools, human approval
- The field moves monthly — track OWASP LLM + ATLAS

<!-- Recap. Cold-call: "the agent read a malicious email and wired money — which leg of privilege+input+channel would you cut, and how?" ~2 min. -->

---

# Questions?
Next week: DevSecOps — putting it together

<!-- Cliffhanger: "Next week we wire the whole course into one CI/CD pipeline — Red vs Blue: sneak a vuln past the gate, or block it." -->
