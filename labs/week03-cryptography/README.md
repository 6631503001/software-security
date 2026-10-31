# Week 3 — Cryptography Used Correctly (and Misused)

**OWASP 2025:** A04 Cryptographic Failures · **CWE:** CWE-327, CWE-916, CWE-330

## ✅ This week — what to do
1. **Before class** — Docker Desktop working (Week 1 *Lab 0*); skim last week's recap.
2. **Slides, then class** — read `slides/week03.md` and answer the worksheet's **Part 2** before class; class opens with the weekly quiz (~10 min) and a short explanation + demo (~15 min).
3. **Lab (in class)** — play this week's game, then complete **Worksheet 3** (`worksheet.md`, Parts 1–4, incl. *Audit the AI* + *EiPE/Prompt*). Kickoff: `docker compose up`. Part 3 marks each task *in class* or *homework*.
4. **Submit before the next class** (homework tasks included) — worksheet PDF → `learn.zcr.ai/submit` · code → GitHub · weekly quiz → `learn.zcr.ai/quiz`. (How: [SUBMISSION.md](../../SUBMISSION.md).)
5. **Project** — apply this week's lesson to your [NoteVault project](../../project/README.md) where it fits.

*Time breakdown: [AGENDA.md](../../AGENDA.md). Grading: see the worksheet rubric.*

## Objectives
- Distinguish hashing vs encryption vs encoding.
- Store passwords with a vetted KDF (bcrypt/argon2).
- Recognize crypto misuse: ECB, hardcoded keys, weak RNG, MD5/SHA-1.

## 🔓 Signature game — "Capture the Hash"
1. **Crack weak hashes:** given unsalted MD5 hashes, recover passwords (e.g. `hashcat`/`john` with a wordlist).
2. **ECB oracle:** observe identical plaintext blocks → identical ciphertext; exploit to leak structure.
3. **Remediate:** rewrite the sample service to use argon2id for passwords and AES-GCM (authenticated) for data, with keys from a secrets manager / env (never hardcoded).

## Deliverable
Before/after code + a short note on which CWE each change closes.

## References
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html
