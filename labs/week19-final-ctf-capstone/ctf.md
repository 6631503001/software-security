# Final — Capstone CTF Tournament (Week 19)

**Course:** Software Security (KOSEN69) · **Covers:** the whole term
**Time:** 150 min · **Total:** 165 pts · **Team-based** · leaderboard · Sandbox only (ethics policy applies).

> Submit per challenge: the **flag** (or noted proof), the **payload/command**, and a **one-line mitigation**. Difficulty rises with points. (The graded project demo is scored separately — see the [project rubric](../../project/README.md).)

**Targets — graded flags come from *your own* instance in the hosted CTFd** (account + WireGuard VPN setup: [arena-vpn-guide](../../docs/arena-vpn-guide.md)) for challenges 1–8, 12 and 14 (#8 Smash is hidden on CTFd until the sitting opens). Challenges 9, 10, 11 and 13 have no hosted instance and use the lab folders locally. Running a lab folder locally (`docker compose up`, or `make` for #8) is practice only: it serves public practice flags (e.g. `FLAG{..._demo}`), which are not a valid submission for a challenge that has a hosted instance.

![A two-column exam blueprint showing the 165-point capstone CTF split across seven categories on the left, feeding via a funnel into the seven-step term project demo pipeline on the right, with the flag-payload-mitigation submission format tying the two halves together.](img/capstone-map.svg)

| # | Title | Topic / target | Pts |
|---|-------|----------------|-----|
| 1 | **Boolean Bypass** | SQLi login (week04) | 10 |
| 2 | **Shell Out** | command injection (week04) | 15 |
| 3 | **Persistent Pop** | stored XSS (week05) | 10 |
| 4 | **Not Your Object** | IDOR (week06) | 10 |
| 5 | **Token Smith** | forge JWT to admin (week06) | 15 |
| 6 | **BOLA (API)** | broken object-level authorization (week10) | 8 |
| 7 | **Mass Assignment** | bind a privileged field the server should not accept (week10) | 7 |
| 8 | **Smash** | stack overflow → `win()` ret2win (week11) | 20 |
| 9 | **Fuzz First** | crash the binary with a fuzzer (week11) | 10 |
| 10 | **Bad Dependency** | find the vulnerable dep / unsigned image (week12) | 10 |
| 11 | **Misconfig Hunt** | exposed secret / `*:*` IAM / root Dockerfile (week13) | 15 |
| 12 | **Jailbreak the Bot** | prompt injection → leak the secret (week14) | 10 |
| 13 | **Indirect Hit** | indirect injection / output XSS (week14) | 10 |
| 14 | **Break the Build** | `/admin` fails open on a malformed token (week15) | 15 |

> **Note (8 Oct 2026):** #6/#7 were one combined "Raid the API" challenge on an earlier draft of this
> sheet; the hosted CTFd host already runs BOLA and Mass Assignment as two separate challenge
> instances, so this sheet now matches that rather than requiring a rebuild. Point split (8/7) is a
> provisional even-ish division of the old combined 15 and can be rebalanced freely — nothing depends
> on these exact numbers. (The CTFd scoreboard's own dynamic point values for these two are a
> *different*, much larger scale used only for engagement/leaderboard purposes — not the number to
> copy onto this capstone sheet.)
>
> **Note (9 Oct 2026):** #14 "Break the Build" was already live on the hosted CTFd (image
> `airsec/w15-devsecops:dev`, a bake of week15's `insecure_service.py`) but missing from this sheet —
> Week 15 otherwise had no capstone challenge at all. Added at 15 pts (no new build needed); total
> moved from 150 to 165.

**Submission table**

| # | Flag / proof | Payload or command | Mitigation |
|---|---|---|---|
| 1–14 | | | |

*Rules:* attack only provided targets; one submission per team per challenge; document method. First-blood bonus at instructor's discretion.
