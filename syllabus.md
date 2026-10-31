# Software Security 2 — Course Syllabus & Outline (KOSEN-KMITL)

**Subject code:** 02005094 · **Category:** Compulsory (C) · **Department:** Computer
**Level:** Year 4 · **Term:** Semester 2, AY2026 (Nov 2026 – Mar 2027)
**Credits:** 1.5 · **Class time:** 150 minutes a week (3 slots), 20 weeks
**Instructors:** Nutthakorn Chalaemwongwan · Shinya Oyama
**Prerequisites:** Programming (Python/C), Data Structures, Operating Systems basics, Computer Networks (recommended)
**Format:** Supervised hands-on lab practice, supported by brief explanations and demonstrations
**Last updated:** October 2026 — aligned with the official KOSEN-KMITL subject sheet for 02005094; where the two differ, the subject sheet applies.

---

## 1. Course Description

This course teaches students how software fails under attack and how to build software that resists it. It blends timeless fundamentals (memory safety, injection, authentication, cryptography misuse) with the threats that dominate modern systems: **software supply-chain attacks, cloud and container misconfiguration, API abuse, and the security of AI/LLM-powered applications.**

The course is deliberately hands-on. Most class time is supervised lab practice: after a brief explanation and demonstration, students either *break* an intentionally vulnerable target in a safe sandbox or *defend* code they write themselves, re-test, and record the evidence, with instructor feedback on their results and reasoning. Students leave able to threat-model a system, find and exploit common vulnerability classes, remediate them, and integrate security checks into a CI/CD pipeline.

The course is aligned with current industry references including the **OWASP Top 10 (2025)**, the **OWASP Top 10 for LLM Applications (2025)**, the **OWASP API Security Top 10**, **MITRE ATT&CK / CWE**, and the **SLSA** supply-chain framework.

---

## 2. Learning Outcomes

By the end of the course, students will be able to:

1. **Threat-model** a software system and reason about its attack surface, trust boundaries, and adversary capabilities.
2. **Identify and exploit** common vulnerability classes (injection, broken access control, memory-safety bugs, insecure design) in a controlled environment.
3. **Write and review secure code**, applying input validation, output encoding, safe defaults, and least privilege.
4. **Apply cryptography correctly**, recognizing common misuse and selecting appropriate primitives.
5. **Secure the modern software supply chain** using dependency analysis, SBOMs, artifact signing, and build provenance.
6. **Secure cloud, container, and API workloads**, including IAM, secrets management, and configuration hardening.
7. **Assess and defend AI/LLM-powered applications** against prompt injection, insecure output handling, and excessive agency.
8. **Integrate security into the development lifecycle** (SAST, DAST, SCA, secret scanning) within a CI/CD pipeline (DevSecOps).
9. **Disclose vulnerabilities responsibly** and communicate risk to technical and non-technical stakeholders.
10. **Reason adversarially** — given a system, generate plausible attacker goals, work out what an attacker with limited knowledge and budget would actually try first, and explain *why* a control does or does not stop them. This is the disposition the other nine outcomes are in service of, and it is assessed directly: in the Week 1 systems-level pass, in every worksheet's abuse cases, and as a scored dimension of the midterm and final CTF.

**Relationship with the Diploma Policy (learning outcomes)**

- **C(2)** Ability to understand the operating system and to develop software to solve specific problems.
- **C(4)** Ability to understand the computer network system and security methods and to implement the safe system within networks, servers, computers, and connected devices.
- **G(5)** As an engineer, attitude to act with awareness of social roles and responsibility to make a better society.

---

## 3. Why This Course Is "Modern"

Traditional software-security courses stop at buffer overflows and SQL injection. Those still matter and are covered here — but the 2025 threat landscape has shifted toward **design-level and dependency-level failures**. The OWASP Top 10:2025 made this explicit by adding **Software Supply Chain Failures** as a new top-tier category and elevating **Security Misconfiguration** to #2. This course reflects that shift and adds two areas most curricula still lack:

- **Software supply-chain security** (SLSA, SBOMs, Sigstore/Cosign, dependency confusion, typosquatting).
- **AI/LLM application security** (the OWASP LLM Top 10, prompt injection, RAG/vector-store risks, agentic systems).

---

## 4. Lab Environment

All offensive work is performed **only** against instructor-provided, intentionally vulnerable targets inside an isolated sandbox. Students never attack systems they do not own or lack written permission to test.

**Required toolkit (all free / open source) — Docker-first:**

- **Docker Desktop** (Windows / macOS / Linux) — runs every lab target via `docker compose up`. *No full VM required.*
- **Lab toolbox container** (`labs/toolbox`) — a small Linux image with `clang`+libFuzzer, `gdb`, `nmap`, `sqlmap` for the weeks that need Linux dev/attacker tools (mainly **Week 11**).
- **Git + a GitHub account** — for labs, CI/CD, and the term project.
- Browser with **Burp Suite Community** or **OWASP ZAP** — web/API testing proxy.
- *Optional fallback:* a **Kali/Ubuntu VM** (VirtualBox/UTM) if your host can't run Docker.

**Pre-built vulnerable targets used during the term:**

- **OWASP Juice Shop** — modern web app vulnerabilities.
- **OWASP WebGoat** — guided web-security lessons.
- **DVWA** (Damn Vulnerable Web Application).
- **crAPI / Damn Vulnerable Web Services** — API security.
- **pwn.college / picoCTF / OverTheWire** — binary and systems exploitation.
- **Gandalf / a self-hosted vulnerable LLM chatbot** — prompt-injection practice.

A one-page **"Lab 0" setup guide** is provided before Week 1: the whole environment stands up in under an hour via a single `docker compose up`, so do it **before** the first class — class time is for the lab itself.

---

## 5. Weekly Outline (20 weeks)

> Each teaching week is one **150-minute class**: a ~10-min weekly quiz → a ~15-min explanation and demonstration → ~125 min of **supervised lab** (the signature game, then the defend/fix task). The full concept material is **pre-class** (the week's slides), and the worksheet's Part 2 questions are answered before class. Tasks that do not fit the class are **homework**, marked task by task on each worksheet — see [AGENDA.md](AGENDA.md). The course runs **12 teaching weeks** (1–6, 10–15), **1 capstone week** (16), **2 reflection/review weeks** (7, 17), **2 exam blocks** (8–9 midterm, 18–19 final) and **1 feedback week** (20).

| Block | Weeks |
|---|---|
| Unit A — Foundations | 1–3 |
| Unit B — Web App Security | 4–6 |
| 🔁 Reflection & Review (pre-midterm) | **7** |
| 📝 Midterm | **8–9** |
| Unit C — Systems & Modern Stack | 10–16 |
| 🔁 Reflection & Review (pre-final) | **17** |
| 📝 Final exam | **18–19** |
| 🗒️ Examination feedback & course reflection | **20** |

### Unit A — Foundations (Weeks 1–3)

**Week 1 — Security Mindset & Threat Modeling**
*Concepts:* CIA triad; attacker vs. defender mindset; trust boundaries; attack surface; STRIDE; the OWASP/MITRE landscape (Top 10, CWE, ATT&CK); **"Secure by Design" (CISA)** framing. Maps to **A06:2025 Insecure Design**.
*🎲 Game — "Elevation of Privilege":* play Microsoft's STRIDE card deck against a provided app's DFD; build a STRIDE threat model + attack-surface map. Lab 0 environment setup.

**Week 2 — Secure SDLC & Tooling**
*Concepts:* Where security fits in the SDLC; SAST vs. DAST vs. SCA vs. **fuzzing**; secret scanning; "shift left" and DevSecOps overview.
*🏁 Game — "Bug Triage Race" + "Fuzzing Race":* run Semgrep + Gitleaks on a flawed repo and triage by CWE (scored); intro coverage-guided fuzzing (first crash wins).

**Week 3 — Cryptography Used Correctly (and Misused)**
*Concepts:* Hashing vs. encryption vs. encoding; symmetric/asymmetric basics; password storage (bcrypt/argon2); TLS overview; common failures (ECB, hardcoded keys, weak randomness, MD5/SHA-1). Maps to **A04:2025 Cryptographic Failures**.
*🔓 Game — "Capture the Hash":* crack weak hashes + break an ECB oracle (speedrun), then remediate with a vetted KDF and authenticated encryption.

### Unit B — Web Application Security (Weeks 4–6)

**Week 4 — Injection & Input Handling**
*Concepts:* SQL injection, command injection, the general injection pattern; parameterized queries; output encoding. Maps to **A05:2025 Injection**.
*⚔️ Game — "SQLi Warm-up":* tiered injection challenges in DVWA / Juice Shop; rewrite endpoints with prepared statements + validation.

**Week 5 — Cross-Site Scripting (XSS) & Client-Side Risks**
*Concepts:* Reflected/stored/DOM XSS; CSRF; SameSite cookies; Content Security Policy; same-origin policy.
*⛳ Game — "XSS Golf":* shortest payload that pops `alert(1)` / steals a cookie wins; then deploy a CSP + escaping that blocks every payload; demo CSRF + defense.

**Week 6 — Authentication, Sessions & Access Control**
*Concepts:* Authn vs. authz; session management; JWT pitfalls; OAuth 2.0 / OIDC overview; IDOR and privilege escalation. Maps to **A01:2025 Broken Access Control** and **A07:2025 Authentication Failures**.
*🗺️ Game — "IDOR Treasure Hunt + JWT Forgery":* reach other users' data via object-id tampering, forge a weak JWT; implement RBAC + fix token handling.

### 🔁 Week 7 — Reflection & Review (pre-Midterm)
No new content. Consolidate Weeks 1–6. *🎯 "Security Jeopardy" team quiz-show + a mock CTF in the midterm format.* Deliverable: a one-page cheat sheet.

### 📝 Weeks 8–9 — Midterm (covers Weeks 1–6)
- **Week 8 — Written/concept exam:** threat modeling, CWE/OWASP mapping, "spot the vuln," secure-design short answers.
- **Week 9 — Hands-on CTF practical:** graded challenges across injection, XSS, auth/IDOR, and crypto in the sandbox.

### Unit C — Systems & Modern Stack (Weeks 10–16)

**Week 10 — API Security**
*Concepts:* REST/GraphQL attack surface; the **OWASP API Security Top 10** (BOLA, broken authentication, excessive data exposure, mass assignment, resource consumption).
*🥷 Game — "crAPI Raid":* exploit BOLA + mass assignment, then add authorization, schema validation, and rate limiting.

**Week 11 — Memory-Safety & Exploitation** *(merges former memory-safety + RE weeks)*
*Concepts:* C/C++ memory model; stack buffer overflows; integer overflow; use-after-free; format-string bugs; mitigations (ASLR, canaries, NX/DEP); intro to `gdb`/Ghidra; **the global shift to memory-safe languages (CISA/ONCD roadmaps).**
*💥 Game — "Fuzzing Race → Pwn the Binary":* fuzz to find the bug (AFL++/libFuzzer), exploit a stack overflow / format string, watch canaries+ASLR break it, then **rewrite the routine in Rust** and explain why the bug class disappears.

**Week 12 — Software Supply-Chain Security** *(merges former dependencies + integrity weeks)*
*Concepts:* Why the supply chain is now top-tier (**A03:2025**); dependency confusion, typosquatting, malicious/transitive packages; SBOMs (CycloneDX/SPDX); **SLSA** provenance; **Sigstore/Cosign** signing (**A08:2025**).
*📦 Game — "Dependency Confusion Heist":* plant/identify a typosquatted package in a controlled registry; then generate an SBOM, sign & verify with Cosign, and add a provenance gate.

**Week 13 — Cloud & Container Security**
*Concepts:* Shared-responsibility model; IAM least privilege; secrets management; container image hardening; Kubernetes basics; **A02:2025 Security Misconfiguration**.
*🔍 Game — "Misconfig Hunt" (CloudGoat-style):* find & fix an over-permissive IAM policy, an exposed bucket, env-var secrets, and a vulnerable Dockerfile (scan + harden with Trivy).

**Week 14 — Security of AI / LLM-Powered Applications**
*Concepts:* **OWASP Top 10 for LLM Applications (2025)** — prompt injection (LLM01), sensitive info disclosure, insecure output handling, excessive agency, RAG/vector weaknesses, unbounded consumption; **agentic-AI / MCP risks (MITRE ATLAS, post-Oct 2025)**.
*🧙 Game — "Gandalf Challenge":* direct + indirect prompt injection to exfiltrate a secret; demo tool poisoning / excessive agency in an agent; add guardrails, output validation, and **least-privilege tool access**, then re-test.

**Week 15 — DevSecOps: Putting It Together**
*Concepts:* Logging, monitoring & alerting (**A09:2025**); failing safely (**A10:2025**); secure CI/CD; vulnerability management; coordinated disclosure & bug bounties; **Secure by Design**.
*🔴🔵 Game — "Break the Build" (Red vs Blue):* Blue builds a GitHub Actions gate (Semgrep + Trivy + Gitleaks) that **fails on high-severity findings**; Red submits PRs trying to sneak vulns past it.

**Week 16 — Capstone Studio & CTF Warm-up**
*Studio:* Work-in-progress capstone demos (attack → root cause → fix) + a practice CTF tournament previewing the final; cross-team peer review.

### 🔁 Week 17 — Reflection & Review (pre-Final)
Consolidate Weeks 10–16 (+ first-half callbacks). *🎯 "Security Jeopardy: Champions Edition" + a mock final CTF in the Week-19 format.*

### 📝 Weeks 18–19 — Final Exam
- **Week 18 — Written exam:** cumulative, with emphasis on Weeks 10–16 (API, memory safety, supply chain, cloud, AI/LLM, DevSecOps).
- **Week 19 — Capstone CTF tournament + final project demos:** a full term-spanning CTF plus each team's secured-build demo video, submitted with the report (threat model → vulns → remediation → SBOM/signing → CI pipeline).

### 🗒️ Week 20 — Examination Feedback & Course Reflection
No new content and nothing graded. Review your assessment feedback, work through corrections, discuss recurring misconceptions, and connect your assessment evidence to the course learning outcomes.

---

## 6. Assessment

| Component | Weight | Graded |
|---|---|---|
| Weekly lab worksheets — 13 graded | 30% | **Individual** |
| Midterm — Week 8 (written) + Week 9 (CTF practical) | 20% | **Individual** |
| Final — Week 18 written *(individual)* + Week 19 capstone CTF *(team)* | 25% | Mixed |
| Term project (secure build + threat model + remediation report) | 15% | **Team of 2–3** |
| Weekly quizzes (drop lowest 1–2) + participation / **Houses** leaderboard | 10% | Individual + Houses |

> **Individual vs team.** Your grade is dominated by **individual mastery** (worksheets,
> quizzes, exams = ~75%). **Team** work is bounded (project 15% + the Week 19 capstone CTF).
> The fun **weekly games** (Bug Triage Race, XSS Golf, the CTFs, …) score toward the **Houses
> leaderboard under participation** — they drive engagement, **not** the 30% worksheet grade,
> so a quiet teammate can't pull your mark down.

**Ability split (per the subject sheet).** The same 100 points, by the ability each component assesses:

| Component | Basic | Technical | Interdisciplinary | Total |
|---|---:|---:|---:|---:|
| Midterm | 10 | 10 | 0 | 20 |
| Final | 5 | 20 | 0 | 25 |
| Quizzes / participation | 5 | 5 | 0 | 10 |
| Lab work (weekly worksheets) | 0 | 25 | 5 | 30 |
| Term project | 0 | 10 | 5 | 15 |
| **Total** | **20** | **70** | **10** | **100** |

**Worksheet versions.** Each student completes the weekly worksheets in an assigned version — **Conventional** or **AIR-Sec**. Follow the version you are assigned. Both versions use the same component weights and the same course rubric below.

**Course rubric (subject sheet).** The course-level evaluation rubric: these six criteria describe what *very good*, *good* and *fail* look like across the course. Each worksheet and the term project keep their own point rubrics, which assess these criteria.

| Criterion | Very good (ideal) | Good (standard) | Fail (unacceptable) |
|---|---|---|---|
| Threat modeling and risk analysis | Accurately models assets, boundaries and attacker goals; prioritizes plausible risks and connects controls to documented threats. | Identifies main assets, boundaries and threats; provides workable risk priorities with minor gaps. | Omits essential boundaries or attacker goals, or proposes risks and controls without defensible reasoning. |
| Vulnerability analysis and evidence | Reproduces vulnerabilities with clear evidence, correct CWE/OWASP mapping and an accurate explanation of root cause and impact. | Reproduces core vulnerabilities and explains their impact; evidence or classification has minor omissions. | Cannot reproduce or explain key findings, or presents unsupported vulnerability claims. |
| Secure remediation and verification | Implements appropriate root-cause fixes; demonstrates failed original attacks and preserved legitimate behavior using repeatable tests. | Implements a functional fix and verifies the principal attack is blocked, with limited coverage or explanation. | Leaves the root cause unresolved, breaks essential behavior, or provides no credible verification. |
| Security tooling and secure delivery | Selects suitable tools, triages findings accurately, and demonstrates effective dependency, artifact-integrity and CI security controls. | Runs appropriate tools and applies essential controls; interpretation or integration has minor gaps. | Cannot operate required tools, misinterprets critical findings, or lacks functioning security controls. |
| Critical evaluation and communication | Critiques security advice with evidence; explains mechanisms clearly and delivers a coherent, reproducible technical report and accessible summary. | Identifies major errors and communicates findings and fixes clearly, with some missing justification or detail. | Repeats unverified advice, cannot explain the work, or provides an unclear and unsupported report. |
| Ethics, integrity and contribution | Consistently follows scope and disclosure rules; provides attributable evidence, disclosure of any AI assistance and a clear individual contribution history. | Follows authorized scope and documents original work and any AI assistance, with minor record-keeping omissions. | Fails to demonstrate authorized, attributable work or omits essential integrity and contribution evidence. |

**Term project.** In teams of 2–3, students take a small web/API application, threat-model it, find and document its vulnerabilities, remediate them, generate an SBOM, sign the release artifact, and wire up a security CI pipeline. Deliverables: a threat model, a vulnerability report mapped to CWE/OWASP, the fixed code, and a short demo. Each member's mark is scaled by a short **peer-contribution evaluation** (see `project/README.md`).

**Term project rubric (100 pts, scales the 15% above):**

| Criterion | Pts |
|---|---|
| Threat model quality & completeness | 20 |
| Vulnerability findings (correctness, CWE/OWASP mapping, depth) | 25 |
| Remediation quality (correct, minimal, well-explained) | 25 |
| Supply-chain hardening (SBOM + signing + provenance) | 15 |
| CI pipeline (works, fails build appropriately) | 10 |
| Presentation & report clarity | 5 |

**Teams & Houses.** Two layers, one structure:
- **Houses** — large, persistent, **mixed-ability** groups for the whole term. They drive the season-long **CTFd leaderboard**, Hall of Fame, and the weekly games. **Houses are not graded** (pure engagement — free-riding can't affect anyone's grade).
- **Project teams of 2–3** **nest inside** a House. This is the only *graded* group unit, protected by per-student flags + the peer-contribution evaluation.

**Deadlines and late submissions.** Each week's worksheet and code fix are due at **23:59 (Thai time,
ICT) the night before the next week's class**, i.e. **Monday 23:59** for the Tuesday class; the exact time is shown on `learn.zcr.ai/submit`. The term
project's deadlines are in [project/README.md](project/README.md). Late work loses **10% of that
item's score for each started 24 hours** after the deadline, so it reaches **0 after 10 days**, and the
portal stops accepting it after day 10. Weekly quizzes are the exception — they're timed and taken
in class, so there is no late window (an absence there is covered instead by the drop-lowest-1–2
rule in the table above). Documented emergencies (medical, bereavement) get a case-by-case
extension at the instructor's discretion, arranged before the deadline where possible.

---

## 7. Academic Integrity & Ethics Policy

All offensive techniques are taught for **defensive and authorized testing** purposes only. Students must:

- Attack only the targets provided in the course sandbox or systems for which they hold **explicit written authorization**.
- Never use course material against third-party systems, the university network, or fellow students.
- Follow **responsible/coordinated disclosure** if they incidentally discover a real vulnerability.

Violations are treated as serious academic-integrity and conduct breaches. Students sign an ethics acknowledgment in Week 1.

---

## 8. Reference Materials

**Primary references (free, current):**

- OWASP Top 10:2025 — https://owasp.org/Top10/2025/
- OWASP Top 10 for LLM Applications (2025) — https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
- OWASP API Security Top 10 — https://owasp.org/API-Security/
- OWASP Cheat Sheet Series — https://cheatsheetseries.owasp.org/
- MITRE CWE Top 25 & ATT&CK — https://cwe.mitre.org/ , https://attack.mitre.org/
- SLSA (Supply-chain Levels for Software Artifacts) — https://slsa.dev/
- Sigstore — https://www.sigstore.dev/

**Recommended books:**

- *The Web Application Hacker's Handbook* — Stuttard & Pinto.
- *Hacking: The Art of Exploitation* — Jon Erickson (for the memory-safety unit).
- *Alice and Bob Learn Application Security* — Tanya Janca (modern, beginner-friendly).
- *Building Secure and Reliable Systems* — Google/O'Reilly (free online).

**Practice platforms:** PortSwigger Web Security Academy (free), picoCTF, OverTheWire, pwn.college, Hack The Box / TryHackMe (intro tracks).

---

## 9. Mapping to OWASP Top 10:2025

| OWASP 2025 Category | Where covered |
|---|---|
| A01 Broken Access Control | Week 6 |
| A02 Security Misconfiguration | Week 13 |
| A03 Software Supply Chain Failures | Week 12 |
| A04 Cryptographic Failures | Week 3 |
| A05 Injection | Weeks 4–5 |
| A06 Insecure Design | Weeks 1, 15 |
| A07 Authentication Failures | Week 6 |
| A08 Software or Data Integrity Failures | Week 12 |
| A09 Security Logging & Alerting Failures | Week 15 |
| A10 Mishandling of Exceptional Conditions | Week 15 |

*Plus dedicated modern coverage beyond the core Top 10: API Security (Week 10), memory safety/exploitation + fuzzing (Week 11), and AI/LLM + agentic security (Week 14).*
