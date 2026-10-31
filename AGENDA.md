# Weekly Agenda & Time Plan — KOSEN-KMITL 02005094

**Class time:** **150 min/week** (3 slots) over **20 weeks**, per the official subject sheet
(Software Security 2, 1.5 credits). Most of the class is supervised lab practice; brief
explanations and demonstrations support it.

- **Before class:** the week's slides (the full concept material — what used to be a 120-min
  lecture) and the worksheet's **Part 2** questions.
- **In class:** a short quiz, a brief explanation + demo, then the worksheet's *in class* tasks.
- **After class (homework):** the worksheet's *homework* tasks, Part 4, *Audit the AI* and
  *Comprehension & Prompt*. Everything is submitted before the next class.
- **Quizzes:** a short **weekly quiz (~10 min) at the start of every teaching week** (retrieval
  practice, low-stakes, drop lowest 1–2). Two **cumulative review quizzes** (25 pts) run in the
  review weeks (W7 pre-midterm, W17 pre-final).

> **Timetable: one contiguous 150-min block** (3 consecutive slots; confirmed by the owner
> 2026-10-31). Everything below — the teaching-week template, the Docker start-up, and the 150-min
> exams in Weeks 9, 18 and 19 — depends on it; re-plan if the timetable ever splits the slots.

---

## Standard teaching-week template (Weeks 1–6, 10–15) — 150 min

| Time | Block |
|------|-------|
| 0:00–0:10 | **Weekly quiz** (retrieval) + today's goal |
| 0:10–0:25 | **Brief explanation + live demo** of the week's flaw and its fix — the full concepts are pre-class |
| 0:25–2:30 | **Supervised lab:** the worksheet's *in class* tasks — the signature game, then the defend/fix task (≤125 min). The instructor circulates, checks evidence and reasoning, and runs 2–3 **viva spot-checks** |

Submission (worksheet PDF → `learn.zcr.ai/submit`, fix → GitHub) is due at **23:59 the night before the next
week's class** (Monday 23:59 for the Tuesday class), homework tasks included. Late work loses 10% per started day and reaches 0 after 10 days
(`syllabus.md` §6).

> **Why there is no in-class micro-demo any more.** In a 150-min class the time goes to the lab.
> "Explain it live" is carried by the **viva spot-checks** during the lab — which double as the
> anti-AI control — and by the capstone (W16 WIP studio + the W19 demo video).
>
> **Every teaching week's worksheet** has four graded parts beyond the lab tasks:
> **Evidence & Integrity** (identity-stamped proof), **Audit the AI** (critique an AI answer),
> **Explain-in-Plain-English** + **Prompt Problem**. The live **CTFd / Houses scoreboard**
> (if running) is shown at the start/end of class.

### How each worksheet is split

Each worksheet's Part 3 now says which tasks are **in class** and which are **homework**. The rule:
the tasks the subject sheet's *Method* line for that week says happen in class, plus the defend/fix
task, stay in class; project-target tasks, extensions and write-ups go home. **Week 1 is the
exception:** its Method line is modelling only (sandbox, trust boundaries, the card exercise), so its
rank-and-fix Task 8 is homework. **No task's minutes and no rubric changed** — only where each task
is done.

| Wk | Worksheet budget | In class | Before class | Homework |
|----|:---:|---|---|---|
| 1 | 220 | Tasks 0, 1, 2, 3, 3b, 4 — **125** | — | Tasks 5, 6, 7, 8 — **95** |
| 2 | 180 | Tasks 0, 1, 2, 3, 4, 7, 8 — **115** | — | Tasks 5, 6 — **65** |
| 3 | 180 | Tasks 0, 1, 2, 3, 4, 7, 9 — **115** | — | Tasks 5, 6, 8 — **65** |
| 4 | 150 | Tasks 0, 1, 2, 3, 5 — **125** | — | Task 4 — **25** (Task 5's upload re-test goes with it) |
| 5 | 150 | Tasks 0, 1, 2, 4, 5 — **125** | — | Task 3 — **25** |
| 6 | 150 | Tasks 0, 1, 2, 3, 5 — **125** | — | Task 4 — **25** (Task 5's `/api/admin` re-test goes with it) |
| 10 | 145 | Tasks 0, 1, 2, 3, 5 — **125** | — | Task 4 — optional bonus, **20** |
| 11 | 145 | Tasks 0, 1, 2, 4 — **120** | — | Task 3 — **25** |
| 12 | 150 | Tasks 0, 2, 3, 4 — **115** | — | Task 1 — **35** |
| 13 | 180 | Tasks 1, 2, 4 — **120** | Task 0 — **15** | Tasks 3, 5 — **45** |
| 14 | 180 | Tasks 0, 1, 2, 5 — **120** | — | Tasks 3, 4 — **60** |
| 15 | 205 | Tasks 0, 1, 1b, 2 — **110** | — | Tasks 3, 4, 5 — **95** (see the Week 15 note below) |

Weeks with less than 125 min in class use the slack for feedback and for students who fell behind.

---

## Per-week time table

| Wk | Type | Quiz | Demo | Lab (in class) | Exam | Class total | Worksheet homework |
|----|------|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | Teach — Threat Modeling | 10 | 15 | 125 | — | 150 | 95 |
| 2 | Teach — SDLC + Fuzzing | 10 | 15 | 115 | — | 150 | 65 |
| 3 | Teach — Cryptography | 10 | 15 | 115 | — | 150 | 65 |
| 4 | Teach — Injection | 10 | 15 | 125 | — | 150 | 25 |
| 5 | Teach — XSS | 10 | 15 | 125 | — | 150 | 25 |
| 6 | Teach — Auth & Access | 10 | 15 | 125 | — | 150 | 25 |
| 7 | 🔁 Review (pre-midterm) | 30‡ | — | — | — | 150 | — |
| 8 | 📝 Midterm — Written | — | — | — | 120 | 150 | — |
| 9 | 📝 Midterm — CTF | — | — | — | 150 | 150 | — |
| 10 | Teach — API Security | 10 | 15 | 125 | — | 150 | 0 (+20 optional) |
| 11 | Teach — Memory Safety | 10 | 15 | 120 | — | 150 | 25 |
| 12 | Teach — Supply Chain | 10 | 15 | 115 | — | 150 | 35 |
| 13 | Teach — Cloud/Container | 10 | 15 | 120 | — | 150 | 60 (15 before class) |
| 14 | Teach — AI/LLM | 10 | 15 | 120 | — | 150 | 60 |
| 15 | Teach — DevSecOps | 10 | 15 | 110 | — | 150 | 95 |
| 16 | Capstone Studio | — | — | 150 | — | 150 | project |
| 17 | 🔁 Review (pre-final) | 30‡ | — | — | — | 150 | — |
| 18 | 📝 Final — Written | — | — | — | 150 | 150 | — |
| 19 | 📝 Final — CTF + Demos | — | — | — | 150 | 150 | — |
| 20 | 🗒️ Exam feedback & reflection | — | — | — | — | 150 | — |

‡Cumulative review quiz (25 pts, 30 min) used to prep for the exam.
"Worksheet homework" counts only the Part 3 tasks marked homework; Part 2 (before class), Part 4
and the AI-resilient parts come on top.

---

## Special-week agendas

### Week 7 & 17 — Review (150 min)
| Time | Block |
|------|-------|
| 0:00–0:30 | **Cumulative review quiz** (quiz1 / quiz2 — 25 pts, 30 min as the quiz files state) |
| 0:30–1:05 | Security Jeopardy team review |
| 1:05–2:20 | Mock CTF in the format of the upcoming exam — the first 75 min in class. It is ungraded practice, so students finish the remaining challenges at home |
| 2:20–2:30 | Debrief: common mistakes + exam logistics |

### Week 8 / 18 — Written exam
- **120 min (midterm) / 150 min (final)**, unchanged — both are graded, so their length is the
  instructor's decision, not this plan's. The Week 18 paper fills the class exactly: seat students
  and hand out papers before the slot starts.

### Week 9 — Midterm CTF practical (150 min)
- 0:00–0:10 rules + target check · 0:10–2:30 solve challenges · submit flags. This fills the class
  exactly (graded, length unchanged): bring the targets up before the slot starts.

### Week 16 — Capstone Studio (150 min)
| Time | Block |
|------|-------|
| 0:00–1:00 | Team WIP demos (attack → root cause → fix) + peer review, run as **paired stations**: each team gives its 10-min demo + 5-min Q&A to one other team, then they swap; the instructor circulates |
| 1:00–2:15 | Practice CTF scrimmage (ungraded; stays open online after class) |
| 2:15–2:30 | Feedback + finalize checklist before the final |

### Week 19 — Final CTF + project demos (150 min)
| Time | Block |
|------|-------|
| 0:00–2:30 | Capstone CTF tournament (whole term, graded, length unchanged) — fills the class |

> **Demo format (decision 2026-10-24).** There is no per-team live demo or Q&A slot. The demo video
> is linked in the report and due with it, and graded asynchronously on the project rubric; only
> teams the instructor flags (report ≠ repo, a similarity hit, work the team can't account for) are
> called for a short live Q&A, outside the CTF time.

### Week 20 — Examination feedback & course reflection (150 min)
| Time | Block |
|------|-------|
| 0:00–0:45 | Assessment feedback: walk through the final written exam and the capstone CTF |
| 0:45–1:30 | Corrections: students rework their weakest items and explain the corrected reasoning |
| 1:30–2:05 | Recurring misconceptions — class discussion |
| 2:05–2:30 | Course reflection: connect your assessment evidence to the course learning outcomes |

No new content and nothing graded.

---

## ⚠️ Note — worksheet budgets vs the 150-min class

Worksheet Part 3 budgets run from 145 to 220 min, and none of them fits a 150-min class whole. They
are not trimmed: each worksheet marks its tasks *in class* or *homework* (table above).

- **Week 1 adds up to 220 min, not 180.** Task 3b (the systems-level pass) was added after the
  rest of the worksheet was timed; this file used to list Week 1 as matching a 180-min block.
- **Week 10's 145 includes a 20-min optional bonus** (Task 4, crAPI Raid), now optional homework,
  so its required content is 125 — exactly the lab block.

**Week 15 over-books on purpose.** Its task budgets total 205, because Tasks 2–4 are dominated by
GitHub Actions queue and scan wall-clock rather than classroom work. Do **not** "fix" this by
re-timing the tasks — Task 4 feeds the Defense score and Task 5 produces the Break-the-Build
scoreboard, so trimming them silently changes graded work.
[The lesson plan](docs/lesson-plans/week15-devsecops-pipeline.md) lists three ways to absorb the
overrun. This plan combines the first two: Tasks 0, 1, 1b and 2 (push the gate) run in class; Tasks
3–5 wait on Actions runs and the Red/Blue results and are homework. Task 1b stays in class.
