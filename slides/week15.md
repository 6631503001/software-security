---
marp: true
theme: default
paginate: true
header: "Software Security · Week 15"
---

# Week 15
## DevSecOps: Putting It Together
Software Security · Nutthakorn Chalaemwongwan

<!-- Final teaching week. Hook: everything we've learned — SAST, SCA, secrets, image scans — only works if it runs automatically on every commit. Today we wire it into one pipeline that turns every bad PR red — and, once those checks are required, blocks the merge. ~2 min. -->

---

## Today

- Security in the CI/CD pipeline
- Logging, monitoring & alerting
- Failing safely
- Vulnerability mgmt & disclosure
- 🎮 Game: **Break the Build** (Red vs Blue)

<!-- Roadmap, 1 min. This week ties the whole course together. Lab is the capstone of the technical units: build the gate (Blue) vs sneak past it (Red). -->

---

## The whole course in one pipeline

- SAST (Wk2) · SCA + image scan (Wk12–13) · IaC (infrastructure-as-code) config scan (Wk13) · secret scanning (Wk2)
- Automated gates instead of one-off scans
- **Secure by Design** as the default

![One app, three layers. You are here: W15. W13, where it runs: a secret baked into an image layer and an IAM policy with Action * on Resource *; fix with a hardened image and least privilege. W14, what it says: the app gets a chatbot; typed text overrides its rules (prompt injection) and its reply goes into the page unescaped (XSS); fix with guardrails, secret redaction and output escaping. W15, how it ships: Semgrep, Trivy and Gitleaks check every push, a red gate fails the PR, and the app denies on error.](img/story-spine.svg)

<!-- The story spine one last time: W13's image and IAM mistakes and W14's injection and XSS are exactly what this pipeline is built to catch on every push. The synthesis slide — walk back through the term: every tool we used by hand now runs automatically on every PR. Manual scanning doesn't scale and humans forget; pipelines don't. ~4 min. -->

---

## One push, three jobs

![The security-ci.yml pipeline at a glance. A push or PR to main starts three jobs in parallel: Semgrep (SAST), Trivy (SCA plus IaC) and Gitleaks (secrets, whole git history). Each job runs the same three phases. The report step never fails (|| true or exit-code "0"). The upload step (if: always()) sends the SARIF to the GitHub Security tab, where every finding of every severity shows. The gate step re-scans and can fail the build. Semgrep's --error and Gitleaks' --exit-code 1 fail on any finding. Trivy's two gates fail only on HIGH or CRITICAL, and the IaC gate is skipped if the SCA gate already failed. The report shows everything; the gate decides.](img/pipeline-at-a-glance.svg)

<!-- Walk it left to right before the YAML: ① report never fails, ② upload always runs, ③ the gate is the step meant to turn the build red — that's Part 2 Q1 in one picture. (An upload can still fail on its own, e.g. a private repo without code scanning — that's why the lab uses a public throwaway repo.) Point at the footnote: the Security tab shows MEDIUM findings like DS-0001 that the gate lets through. ~2 min. -->

---

## A security gate

```yaml
# .github/workflows/security-ci.yml
- semgrep   # SAST
- trivy     # SCA (fs) + IaC (config) — image scan is optional, off by default
- gitleaks  # secrets + git history
# each tool runs TWICE: once to report (SARIF, always), once to gate (fails the build)
```

- The token gets only what it needs: `contents: read`, `security-events: write`
- Results (SARIF) go to the GitHub **Security** tab
- A red run **blocks** a merge only if the jobs are **required checks** (branch protection)

```sim
gate-check
```

<!-- The worked example — this is the lab's actual pipeline. Be precise: Trivy's active jobs are fs (SCA) and config (IaC) — the image-scan step exists in the YAML but is commented out/optional, don't claim it's active. The "runs twice" pattern (report step + separate gate step) is what Part 2 Q1 is built around — say it explicitly. The sim's 2 decoys are the actual worksheet nuance: chmod 777 has no Trivy rule at any severity, while FROM:latest IS detected (DS-0001) but rated MEDIUM and filtered by severity:HIGH,CRITICAL — same green build, different reason. The KEY line is "fail build on HIGH/CRITICAL": a gate that only warns gets ignored. ~6 min. -->

---

## Platform option — GitHub Advanced Security

- **CodeQL** code scanning (SAST) on every PR
- **Secret scanning** + push protection
- **Dependabot** for vulnerable deps
- **SonarQube** as a quality/SAST gate alongside

> Same idea as the YAML gate — managed, in the repo.

<!-- The managed equivalent they'll meet in industry. Same concept, less YAML to maintain. Mention SonarQube as the common quality-gate they'll see in internships. ~3 min. -->

---

## Logging, monitoring, alerting

- **A09:2025** — without logs you can't detect or respond
- Log security events (authn, authz failures, anomalies)
- **Never log the secret/token value itself** (CWE-532) — log `reason=bad_token`, not the token
- Alert on suspicious patterns

<!-- Shift from prevention to detection. A09 (logging/monitoring failures) is a Top 10 risk because you can't respond to what you can't see. The CWE-532 point is graded (Part 2 Q4) and easy to skip if you only say "log security events" — a log line that captures the bad token has just created a new secrets-in-logs problem. Recall W6: we read attacker actions FROM logs — but only if they were logged. ~4 min. -->

---

## Detection tooling

- **NIDS** (network intrusion detection) — Snort / Suricata watch network traffic
- **HIDS** (host intrusion detection) — OSSEC watches one machine
- **SIEM** (collects and connects alerts) — Security Onion bundles these tools
- Network visibility: **TAP** (lossless) vs **SPAN** (cheap, can drop)

<!-- Awareness of the defender's toolkit. NIDS watches the wire, HIDS watches the host, SIEM correlates everything. TAP vs SPAN is a practical gotcha: SPAN ports drop packets under load — you miss attacks. Keep brisk. ~3 min. -->

---

## Alerts — the confusion matrix

| | Incident real | No incident |
|---|---|---|
| **Alert fired** | True positive ✅ | False positive |
| **No alert** | **False negative** 💀 | True negative |

- False negative = worst case (missed attack)
- Some false positives are inevitable — tune, don't silence

<!-- Ties back to W2 triage. The danger asymmetry: a false negative = an attack you never saw. But too many false positives → alert fatigue → analysts mute everything → effective false negatives. The skill is TUNING. ~4 min. -->

---

## When something happens (NIST SP 800-86)

**Collection → Examination → Analysis → Reporting**

- Collect what disappears first (**order of volatility**): memory → temp files → disk → logs
- Failed/success logins: Windows Event **4625 / 4624**

<!-- A taste of incident response / forensics. Order of volatility: capture RAM before you pull the plug — it's gone on shutdown. 4625 (failed) / 4624 (success) are the login events they'd grep in a real investigation. ~4 min. -->

---

## Fail safely

- **A10:2025** — mishandled errors leak info / fail open
- **Fail closed:** deny on error, don't bypass checks
- Don't expose stack traces / secrets in errors

<!-- A design principle that recurs: when something breaks, DENY (fail closed), don't accidentally grant access (fail open). Verbose errors leak schema/secrets (recall W4 error-based enumeration). ~3 min. -->

---

## Vulnerability management & disclosure

- Triage by severity; track to remediation (SLAs)
- **Coordinated disclosure** & bug bounties
- security.txt; a path for researchers to report

<!-- The professional/ethical close: finding a bug is step one; managing it to a fix (with SLAs) is the job. Coordinated disclosure + security.txt = how to receive reports responsibly. Connects to the course ethics theme. ~3 min. -->

---

## One decision, made twice

![Two panels showing the same yes-or-no decision at two different times. Build time: the CI gate's HIGH/CRITICAL severity filter, not the scanner itself, decides what a build refuses — root user (DS-0002, HIGH) is caught, :latest (DS-0001, MEDIUM) slips past the filter. Run time: the /admin handler makes the identical decision on an exception — fail-open returns 200 and logs nothing (silent bypass, A09); fail-closed returns 403 and logs event=authz_failure without ever logging the token itself (CWE-532). At build time, letting MEDIUM through is a risk decision — fine if someone made it on purpose, a gap if nobody looked. At run time, the except branch that returns 200 is the actual fail-open bug: A10, CWE-636.](img/fail-closed.svg)

<!-- The synthesis slide, and arguably the whole course's closing argument: "secure by default" means someone has to have DECIDED the default, twice here — once in YAML severity filters, once in an except block. Keep the two apart: a severity threshold is a policy someone can defend (or not), while an except branch that grants access on error is a bug (A10, CWE-636). Walk both panels, land on the bottom line before the game. ~5 min. -->

---

## Try it — same request, two services

Pick a token. Both real services answer, and you see what each one logs.

```sim
fail-open
```

<!-- Interactive companion to the diagram above; every response and log line was captured from the real :8090/:8091 containers. Click "no token" (8090 leaks, 8091 logs a WARNING), then "user, not admin" (both deny: the bug lives only on the error path), then "real admin" (both unlock). ~3 min. -->

---

## 🔴🔵 Game — Break the Build

- **Blue:** set up the gate (Semgrep + Trivy + Gitleaks), fail on HIGH/CRITICAL, log security events and deny on error
- **Red:** one planted defect per PR — an old dependency (Trivy SCA), a Dockerfile running as root (Trivy config), or a hard-coded token (Gitleaks)
- **Score:** Blue +1 per catch · Red +1 per defect that slips through (e.g. `chmod 777`, `FROM :latest` stay green) — then propose a rule that would catch it
- **Flag:** leak it from the fail-open `/admin` in `insecure_service.py` (local run = demo flag; graded flag = your hosted instance)

<!-- The capstone game. Both roles teach: Blue learns to configure gates, Red learns where gates have blind spots. Task 4 (the graded screenshot) needs a defect that maps to a gate; anything that slips through instead is a Task 5 Red point, exactly as the worksheet scores it. Run it as live PRs against the pipeline. The weekly quiz no longer asks for the gate/what-it-blocks/flag (dropped — quiz runs before the lab) — that's required in the worksheet instead, don't drop the flag half there, it's still graded. ~3 min. -->

---

## Break the Build — what each change turns red

![The Break the Build game board, measured by running security-ci.yml's own gate commands on the real lab files. Columns: Semgrep gate, Trivy SCA gate, Trivy IaC gate, Gitleaks gate. Blue's baseline is red before Red does anything: unpinned @v4/@v3 action tags and host="0.0.0.0" trip Semgrep, and the docs' own curl examples with the toy alice-token header trip Gitleaks' curl-auth-header (a false positive). Red's attacks, one per PR on Blue's green baseline: urllib3==1.24.1 trips only Trivy SCA (7 HIGH, e.g. CVE-2019-11324). A Dockerfile running as root trips Trivy IaC (DS-0002 HIGH) and also Semgrep (missing-user or last-user-is-root). A ghp_ GitHub token trips Gitleaks (github-pat) and also Trivy SCA, whose secret scanner rates it CRITICAL. Decoys stay green: chmod 777 has no rule, and FROM python:latest is DS-0001 MEDIUM, which the gate filters out.](img/break-the-build-board.svg)

<!-- The rules of the game on one board. Top rows = Task 3 (Blue must clear these first or every Red PR is already red); dashed cells = cross-hits, one defect turning two jobs red. ~2 min. -->

---

## Try it — which job goes red?

Click **Blue's clean baseline**, then **Red: old urllib3**, and find the gate that fails.

```sim
red-team-pr
```

<!-- Click "untouched lab" first: Semgrep + Gitleaks are red before Red does anything. Then "Blue's clean baseline", then each Red preset. End on "two defects in one PR": the IaC gate shows skipped, which is why the worksheet says one defect per PR. ~3 min. -->

---

## Task 1b at a glance

![Task 1b at a glance. From the lab folder, docker compose up starts two containers from the same python:3.12-slim image, both mounting the lab folder: insecure_service.py on localhost:8090 and secure_service.py on localhost:8091. Send both the same GET /admin with no token. :8090 answers 200 with the panel and the FLAG, because the USERS dictionary lookup raises KeyError and the except branch grants access; its log shows only a 200 access line. :8091 answers 403 forbidden and logs a WARNING on the security logger (event=authz_failure outcome=deny reason=unauthenticated). Then prove the fix keeps admins in: alice-token still unlocks :8091, and the auto-grader checks both. Submit the flag, both responses and the failing-open except line; a local run returns the public demo flag, the graded one comes from your hosted instance.](img/lab-at-a-glance.svg)

<!-- The lab briefing for path (a), in the order students do it: ① compose up, ② same request to both ports, ③ docker compose logs, ④ alice-token still works. ~2 min. -->

---

## Deliverable

> 📋 **Worksheet 15** — `labs/week15-devsecops-pipeline/worksheet.md` (Part 3) · **start:** push `security-ci.yml` to your own public repo → GitHub Actions; for the flag, `docker compose up` → :8090 (insecure) / :8091 (secure)

- A passing PR that adds the pipeline
- A screenshot of the **failing** gate step for your planted defect, and which job caught it
- The `FLAG{...}` from the fail-open `/admin`, written in the worksheet (graded flag: your hosted instance)
- **+ Audit the AI / EiPE / Prompt Problem** (see worksheet)

<!-- Two separate targets this week, both graded: security-ci.yml is the CI gate; insecure_service.py/secure_service.py (compose, :8090/:8091) is where the local (public demo) flag lives; graded per-student flags come from the hosted instance. The "build failing" screenshot is the proof the gate actually says no — a green pipeline that never fails is useless. The worksheet grades one planted defect (Task 4); encourage all three if time allows. AI-resilient tasks count. This is also the last weekly quiz. -->

---

## Key takeaways

- Automate security gates — humans forget, pipelines don't
- You can't defend what you don't log
- Fail closed; disclose responsibly

<!-- Recap + course wrap of the technical units. Cold-call: "why must the gate FAIL the build, not just warn?" (warnings get ignored). ~2 min. -->

---

# Questions?
Next week: Capstone studio & CTF warm-up

<!-- Wrap: "Teaching is done — next is your capstone: ship something secure, then defend it in the final CTF. Bring your project to the studio." -->
