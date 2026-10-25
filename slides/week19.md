---
marp: true
theme: default
paginate: true
header: "Software Security · Week 19 · Final"
---

# Week 19
## Final — Capstone CTF + Project Demos
The grand finale

<!-- The finale — make it celebratory + high-energy. Before class: graded flags for challenges 1–6 and 11 come from each student's own hosted instance (confirm everyone can log in and reach one); bring up the local targets for 7–10 and 12, open CTFd, set the demo schedule. Confirm projects run. ~2 min. -->

---

## Two parts

1. 🏆 **Capstone CTF tournament** — whole-term, team-based
2. 🎤 **Final project demo videos** — graded (submitted with the report)

<!-- The CTF tournament is the live part. Demo videos were graded beforehand; after the CTF, call aside only the teams you flagged for a short viva-style Q&A. -->

---

## 🏆 CTF tournament

- Web · API · supply chain · cloud · memory safety · LLM/agentic
- Team leaderboard, prizes — the **live CTFd board** (bigger, includes bonus/boss challenges)
- **Graded score** comes from the paper trail: flag/proof + payload + one-line mitigation per challenge

<!-- Run from ctf.md (graded, 12 challenges/150 pts) + exams/item-bank.md (CTF pool, incl. the boss chain). CTFd's live board runs more challenges at different point values for engagement/leaderboard — that scoreboard is NOT the grade; ctf.md's submission is. Dynamic scoring + first-blood bonus on CTFd; announce first-bloods aloud for hype. Prizes for top Houses. -->

---

## 🎤 Final project demo (graded)

Present your secured build end-to-end:

- Threat model → vulnerabilities → remediation
- SBOM + signed artifact
- Security CI/CD pipeline
- **Recorded video walkthrough**, linked in the report and due with it — graded asynchronously on the rubric
- No per-team live slot — the instructor may call a team for a short live Q&A

<!-- Format change (2026-07-26): with N≈80–120 students in teams of 2–3, a 10-min-demo+5-min-Q&A live format needs far more than the 90 minutes this block has — it cannot physically run. Video is graded beforehand on the project rubric (project/README.md) + peer-contribution multiplier; live Q&A only as a viva spot-check for teams the instructor flags (decided 2026-10-24: the final day already holds the written exam and the CTF) — not a re-demo. -->

---

## Bring

- **Video walkthrough link in your report** (due with the report)
- Threat model + vuln report (CWE/OWASP mapped)
- Fixed code, SBOM, signed artifact, CI pipeline

<!-- Checklist — anything missing costs rubric points. Confirm the CI pipeline actually fails on a finding (don't take their word; have them show it in the video). -->

---

# Thank you
You can now threat-model, break, fix, and ship secure software.

<!-- Close the term: name the arc (threat-model → break → fix → ship). Point to next steps (OWASP, CTFs, the readings). For the research: post-test + post-survey happen now (per the study timeline). Celebrate. -->
