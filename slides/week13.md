---
marp: true
theme: default
paginate: true
header: "Software Security · Week 13"
---

# Week 13
## Cloud & Container Security
Software Security · Nutthakorn Chalaemwongwan

<!-- Hook: most cloud breaches aren't clever zero-days — they're a public S3 bucket or a `*:*` IAM policy. Today we hunt and fix those misconfigs. ~2 min. -->

---

## Today

- Shared-responsibility model
- IAM & least privilege
- Secrets management
- Container/image hardening
- 🎮 Game: **Misconfig Hunt**

<!-- Roadmap, 1 min. Theme: the cloud is secure; your CONFIGURATION usually isn't. Lab = find + fix misconfigurations, each one a flag. -->

---

## Recap & framing

- Supply chain → what you build with
- Today → where you run it
- **OWASP A02:2025 Security Misconfiguration** (now #2)

![One app, three layers. You are here: W13. W13, where it runs: a secret baked into an image layer and an IAM policy with Action * on Resource *; fix with a hardened image and least privilege. W14, what it says: the app gets a chatbot; typed text overrides its rules (prompt injection) and its reply goes into the page unescaped (XSS); fix with guardrails, secret redaction and output escaping. W15, how it ships: Semgrep, Trivy and Gitleaks check every push, a red gate fails the PR, and the app denies on error.](img/story-spine.svg)

<!-- 1-min bridge. Misconfiguration jumped to A02 in 2025 — it's not a footnote, it's the second most critical web risk. Then the story spine: one app, three layers — today we package it and give it cloud permissions (W13), next we add an AI chatbot to it (W14), last we put a pipeline in front of all of it (W15). Same root mistake all day: trusting input and defaults nobody checked. ~2 min. -->

---

## Shared responsibility

- Cloud secures *of* the cloud; you secure *in* the cloud
- Misconfig — not provider bugs — causes most breaches
- Defaults are rarely safe

<!-- The mental model students most misunderstand: AWS secures the hardware/hypervisor; YOU secure your buckets, IAM, security groups. Almost every headline cloud breach is the customer's config, not the provider. ~4 min. -->

---

## Whose job is it?

![Shared responsibility for this lab's S3-backed app as two panels split by a line. AWS secures OF the cloud: data centres and hardware, the hypervisor and host OS, the S3 and IAM services themselves, the global network. You secure what you put IN it: the IAM policy (iam-policy-insecure.json, 3 flags), the container image (Dockerfile.insecure, 6 flags including the ENV secret), bucket access and encryption, and network rules such as 0.0.0.0/0 on a database port. Conclusion: all 9 Misconfig Hunt flags sit in your half; none is a provider bug.](img/shared-responsibility.svg)

<!-- Point at the line, then at the two pills: every file the students touch today is on the right. Ask "which of the 9 flags could AWS have fixed for you?" — none. ~2 min. -->

---

## IAM & least privilege

```json
{ "Effect":"Allow", "Action":"*", "Resource":"*" }   // 🚩
```

- Over-broad policies = blast radius
- `Resource:"*"` → **CWE-732** (incorrect permission assignment); `Action:"*"` → **CWE-269** (improper privilege management) — they're graded as two distinct findings on the *same* policy, not one
- Fix: two narrow statements on one bucket — `s3:GetObject` on `app/*` objects, plus `s3:ListBucket` limited by an `s3:prefix` `Condition` — not just a narrower ARN

```sim
iam-scope
```

<!-- The worked example — this `*:*` policy is the Misconfig Hunt round 1 and the quiz. If a credential with this leaks, the attacker owns everything. This is 100% manual review — Trivy's config scanner does not parse standalone IAM JSON at all, say so explicitly so students don't wait for a scanner to flag it. The sim scores Action and Resource independently, live, so "two findings, not one" is something they watch instead of a claim on a slide. Least privilege = smallest possible blast radius. ~6 min. -->

---

## If the key leaks — blast radius

![The same AWS account drawn twice at the same scale. Left, iam-policy-insecure.json (Action star, Resource star, no Condition): the whole account is allowed, with example actions a leaked key can now run — s3 star on any bucket, iam:CreateAccessKey to mint new keys that survive rotation, ec2:RunInstances on your bill, kms:Decrypt, cloudtrail:StopLogging to turn off the audit trail — equals full admin; Action star is CWE-269, Resource star is CWE-732. Right, iam-policy-leastpriv.json: everything is implicitly denied except a small app/* square inside lab-app-bucket, readable via s3:GetObject on app/* objects, plus s3:ListBucket only under the Condition s3:prefix = app/*. Trivy parses neither file; Task 2 is manual review.](img/iam-blast-radius.svg)

<!-- The answer to the cold-call "what does *:* cost you if the key leaks?", drawn. Land on iam:CreateAccessKey: rotating the leaked key doesn't evict an attacker who already minted their own. Right side = iam-policy-leastpriv.json, line for line. ~2 min. -->

---

## Secrets management

- Secrets in env vars / Dockerfile / git = leaked
- Use a secrets manager / vault; rotate
- Scan history (Gitleaks) — recall Week 2

<!-- Connect to W2 (Gitleaks) and W12. A secret baked into an image layer is in every copy of that image forever — `docker history` reveals it. Fix = inject at runtime from a vault + rotate. ~4 min. -->

---

## Where the ENV secret ends up

![From a real build of week13-insecure:lab, the image history as a stack with the newest layer on top: CMD, EXPOSE, RUN chmod -R 777, RUN pip install, COPY dot dot, WORKDIR, then ENV AWS_SECRET_ACCESS_KEY and ENV API_TOKEN, both 0 bytes because the value lives in the image config, then the python:latest base layers. Arrows to three readouts: plain docker history still prints sk_live_supersecret_DO_NOT_DO_ (30 of 34 characters); docker history --no-trunc prints the whole token (the Task 3 command); docker inspect .Config.Env prints both keys in full. A fourth arrow: COPY dot dot copied Dockerfile.insecure itself into /app, so the secret is in a file too. Fix: never put the secret in the Dockerfile, inject it at run time, and rotate the key because every pushed image keeps the old value.](img/image-layer-leak.svg)

<!-- Two misconceptions to kill: "truncated history hides it" (it prints 30 of 34 characters) and "delete it in a later layer" (0B — it's config, not a file). Then the bonus leak: COPY . . shipped the Dockerfile itself. ~3 min. -->

---

## Try it — which layer gives it away?

Real `docker history` / `docker inspect` output from both lab images. Pick a command.

```sim
image-layers
```

<!-- Drive it: insecure + "docker history" (still leaks) → "--no-trunc" (Task 3) → "ls -la /app" (Dockerfile.insecure is in the image). Then flip to hardened: no secret row, no build stage, and no ls at all — distroless. Output was captured from real builds, nothing runs live. ~3 min. -->

---

## Storage & network exposure

- Public buckets, open ports, default creds
- Encrypt at rest + in transit
- Private by default; explicit allow

<!-- The classic trio behind most breaches. `0.0.0.0/0` on a DB port = the internet can reach your database. Default creds = free entry. Principle: deny by default, open deliberately (echoes W6 access control). ~4 min. -->

---

## Container image hardening

```bash
# misconfig scan (Dockerfiles)
docker run --rm -v "${PWD}:/src" aquasec/trivy:latest \
  config --severity MEDIUM,HIGH,CRITICAL /src
# image CVE scan
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy:latest image --severity HIGH,CRITICAL week13-hardened:lab
```

- Multi-stage build: `python:3.11-slim@sha256:...` (compiles) → **distroless** `gcr.io/distroless/python3-debian12@sha256:...` (runs) — a smaller runtime image with no shell/package manager, `USER 65532:65532` (non-root)
- `@sha256:...` **digest** pins, not just a version tag — a tag can be repointed later, a digest can't
- Re-scan to prove reduced findings
- **Trivy only catches 3 of 6 planted defects** (`:latest`, root user, secret-in-ENV) — `COPY . .`, `chmod -R 777`, and unpinned `pip install` need **manual review**, no rule fires

<!-- Hands-on — this is the lab's insecure→hardened Dockerfile, always run dockerized (never a bare local trivy binary), against week13-hardened:lab (not a generic myapp:lab). The Trivy-blind-spot point is the actual lesson of this lab, not an aside — half the graded findings need a human, not a tool. Re-scan to prove improvement. ~5 min. -->

---

## Does Trivy see it?

Fix the six defects one at a time and watch `trivy config` re-score the file.

```sim
trivy-blindspot
```

<!-- Press "fix only what Trivy flags": Failures 0, three defects still in the file — a clean scan is not a clean image. Then "a tag, not a digest": DS-0001 passes python:3.11-slim, but harden.md row 1 wants @sha256. Rules checked against real Trivy 0.76.1 on all 96 combinations: 4 → 0 matches scan.sh. ~4 min. -->

---

## Kubernetes basics (awareness)

- Pod security, network policies, RBAC
- Don't run privileged; limit service-account tokens

<!-- Awareness only (K8s is its own course). Key takeaways: a privileged pod ≈ host root; mounted service-account tokens are a lateral-movement prize. Keep it brief. ~3 min. -->

---

## Same app, shipped twice

![The same app as two container images side by side, insecure vs hardened, six layers compared: mutable :latest tag vs a pinned digest, a baked-in secret vs runtime injection, root user vs distroless non-root, COPY-everything vs a minimal context, world-writable permissions vs read-only, and an unpinned pip install vs a discarded build stage. Below both, the same argument one layer up: the wildcard IAM policy vs the scoped one. The conclusion: Trivy flags only three of the seven defects shown here — the tag, the root user, and the secret. COPY .., chmod 777, the unpinned install, and the IAM JSON all need manual review; there is no rule for any of them.](img/container-hardening.svg)

<!-- The whole lab's argument as one picture — walk it row by row once, landing on the Trivy split at the bottom: 3 rows have a rule ID to cite, 4 don't. That 3-of-7 (or "3 of 6" container-only, per the earlier slide) split is Task 1's actual grading rubric, not trivia. ~5 min. -->

---

## 🔍 Game — Misconfig Hunt

**9 flags** — each misconfiguration **found + explained** = a flag:

1. **Container (6):** `:latest` tag, root user, secret-in-ENV, `COPY . .`, `chmod -R 777`, unpinned `pip install`
2. **IAM (3):** `Resource:"*"` (CWE-732), `Action:"*"` (CWE-269), missing `Condition` scoping

<!-- Explain before lab: 9 flags total, two categories only — no separate bucket/storage flag, no IaC/localstack target exists in this lab. Find AND explain (why it's a finding, which fix applies) = the flag. Q6 of the quiz asks for one misconfig they explained + the principle it violated. ~3 min. -->

---

## Deliverable

> 📋 **Worksheet 13** — `labs/week13-cloud-container/worksheet.md` (Parts 1–4) · **kickoff:** `bash scan.sh` (trivy config over the **Dockerfiles only** — IAM JSON is manual review, Trivy doesn't parse it)

- Before/after IAM policy + Dockerfile, all 9 flags explained
- Trivy reports showing reduced risk (container half only)
- Note on secrets remediation
- **+ Audit the AI / EiPE / Prompt Problem** (see worksheet)

<!-- Before/after artifacts + the trivy delta prove the container-side fix; IAM has no scanner delta to show, it's reasoned/written. Don't let "trivy over Dockerfiles + IAM JSON" stand — that's the exact misconception this lab's own history already fixed once. AI-resilient tasks count. -->

---

## Key takeaways

- Misconfiguration > zero-days as a breach cause
- Least privilege, private-by-default, no secrets in code
- Scan IaC and images in CI

<!-- Recap. Cold-call: "what does a `*:*` IAM policy cost you if the key leaks?" (everything — full blast radius). "Scan in CI" sets up W15. ~2 min. -->

---

# Questions?
Next week: AI / LLM application security

<!-- Cliffhanger: "Next week — the newest attack surface: make an AI assistant ignore its rules and leak secrets, with nothing but text." -->
