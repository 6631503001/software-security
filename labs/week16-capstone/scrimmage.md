# Week 16 — CTF Scrimmage (Final tournament warm-up)

A friendly **cross-team** practice tournament that previews the Week 19 finale.
**Ungraded** (bragging rights + a leaderboard) · ~150 min of challenges — about 75 min in class, and the scrimmage stays open online afterwards · Sandbox only (ethics policy applies).

> Same shape as the Week 19 tournament, lighter and with hints — so teams calibrate
> strategy, division of labor, and the submit format before it counts.

## Format
- Teams of 2–4; live **leaderboard**; **first-blood** bonus per challenge.
- Submit per challenge: flag/proof + payload/command + one-line mitigation.
- Challenges are drawn from the term's lab targets (`docker compose up` each).

## Challenge board (mixed difficulty)

| Pts | Challenge | Target | Hint |
|-----|-----------|--------|------|
| 10 | SQLi login bypass | week04 | username not parameterized |
| 10 | Stored XSS | week05 | raw comment render |
| 15 | IDOR + forged JWT chain | week06 | read others' orders, then `alg:none` to admin |
| 15 | BOLA + mass assignment | week10 | id in URL; `is_admin` in body |
| 20 | ret2win | week11 | offset 72 → `&win` |
| 10 | Find the vulnerable dep | week12 | `trivy fs` |
| 15 | Cloud misconfig hunt | week13 | `trivy config` + IAM `*:*` |
| 10 | Jailbreak the chatbot | week14 | override the system prompt |
| 15 | **Boss:** chain two bugs on the [NoteVault](../../project/starter-app/README.md) starter | project | recon → exploit → escalate |

## After the scrimmage
- Quick retro: what slowed you down? who owns what in Week 19?
- Fix any gaps the scrimmage exposed in your **term project** before the graded demo.

> Solutions live in each lab's `solution_*`/`attack.md`. The **graded** tournament +
> project demos are in [Week 19](../week19-final-ctf-capstone/ctf.md).
