/* iam-scope.js — Week 13 simulation.
 *
 * WHAT THIS IS FOR
 * The deck's own claim is that Action:"*" and Resource:"*" are TWO separate
 * findings on the SAME statement, not one "IAM is bad" flag — that distinction
 * is easy to lose when reading a policy as a whole. This evaluates one
 * statement, field by field, exactly like the worksheet's grading does: does
 * Action contain a wildcard (CWE-269), does Resource contain a wildcard
 * (CWE-732), and is there a Condition narrowing what's actually granted.
 *
 * This mirrors the two real policies this week's lab compares
 * (iam-policy-insecure.json vs iam-policy-leastpriv.json) — not a general
 * IAM linter, just this lab's own two findings, computed from whatever JSON
 * is typed.
 */
(function () {
  "use strict";

  var PRESETS = [
    { label: "iam-policy-insecure.json", v: '{\n  "Effect": "Allow",\n  "Action": "*",\n  "Resource": "*"\n}' },
    { label: "scoped action, wide resource", v: '{\n  "Effect": "Allow",\n  "Action": ["s3:GetObject"],\n  "Resource": "*"\n}' },
    { label: "iam-policy-leastpriv.json (statement 1)", v: '{\n  "Effect": "Allow",\n  "Action": ["s3:GetObject"],\n  "Resource": "arn:aws:s3:::lab-app-bucket/app/*"\n}' },
    { label: "scoped + Condition", v: '{\n  "Effect": "Allow",\n  "Action": ["s3:ListBucket"],\n  "Resource": "arn:aws:s3:::lab-app-bucket",\n  "Condition": {\n    "StringLike": { "s3:prefix": ["app/*"] }\n  }\n}' }
  ];

  function isWildcard(v) {
    if (v === "*") return true;
    if (Array.isArray(v)) return v.some(isWildcard);
    return false;
  }

  var input = document.getElementById("policy");
  var presetsEl = document.getElementById("presets");
  var errEl = document.getElementById("err");
  var findingsEl = document.getElementById("findings");
  var verdictEl = document.getElementById("verdict");
  var explainEl = document.getElementById("explain");

  function finding(cwe, label, bad) {
    var div = document.createElement("div");
    div.className = "iam-scope-finding " + (bad ? "is-bad" : "is-ok");
    div.innerHTML = "";
    var badge = document.createElement("span");
    badge.className = "iam-scope-badge";
    badge.textContent = bad ? "✖" : "✔";
    var text = document.createElement("span");
    text.textContent = (cwe ? cwe + " — " : "") + label;
    div.appendChild(badge);
    div.appendChild(text);
    return div;
  }

  function update() {
    var raw = input.value;
    var stmt;
    try {
      stmt = JSON.parse(raw);
    } catch (e) {
      errEl.textContent = "Invalid JSON: " + e.message;
      errEl.hidden = false;
      findingsEl.innerHTML = "";
      verdictEl.textContent = "";
      explainEl.textContent = "";
      return;
    }
    errEl.hidden = true;
    findingsEl.innerHTML = "";

    // Effect decides whether the wildcards GRANT anything. A Deny with "*"
    // is a guardrail, not a finding, so judge it before the two CWEs.
    var effect = typeof stmt.Effect === "string" ? stmt.Effect : "";
    if (effect !== "Allow" && effect !== "Deny") {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = "not a valid statement — Effect must be \"Allow\" or \"Deny\"";
      explainEl.textContent = "AWS rejects a statement without a valid Effect, so it grants nothing. "
        + "Put \"Effect\":\"Allow\" back to see what the wildcards would grant.";
      return;
    }
    if (effect === "Deny") {
      findingsEl.appendChild(finding(null, "Effect is Deny — this statement only ever takes access away", false));
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "a Deny grants nothing — no wildcard finding";
      explainEl.textContent = "Wildcards are only dangerous in an Allow. \"Effect\":\"Deny\" with Action:\"*\" "
        + "blocks everything it matches, and an explicit Deny beats any Allow. Switch Effect back to \"Allow\" to "
        + "see the two findings.";
      return;
    }

    var actionWild = isWildcard(stmt.Action);
    var resourceWild = isWildcard(stmt.Resource);
    var hasCondition = stmt.Condition && typeof stmt.Condition === "object"
      && Object.keys(stmt.Condition).length > 0;

    findingsEl.appendChild(finding("CWE-269", actionWild
      ? "Action is a wildcard — improper privilege management"
      : "Action is scoped to specific operations", actionWild));
    findingsEl.appendChild(finding("CWE-732", resourceWild
      ? "Resource is a wildcard — incorrect permission assignment"
      : "Resource is scoped to a specific ARN", resourceWild));
    findingsEl.appendChild(finding(null, hasCondition
      ? "A Condition narrows the grant further"
      : "No Condition — nothing narrows the grant beyond Action/Resource", false));

    var badCount = (actionWild ? 1 : 0) + (resourceWild ? 1 : 0);

    if (badCount === 2) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = hasCondition
        ? "2 findings, same statement — wildcards on both, narrowed only by the Condition"
        : "full admin on everything — 2 findings, same statement";
      explainEl.textContent = "Action:\"*\" and Resource:\"*\" are graded separately because they fail "
        + "independently: fixing only one (e.g. scoping Resource but leaving Action:\"*\") still leaves "
        + "the other CWE open. A leaked credential with this statement can do anything to anything.";
    } else if (badCount === 1) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = "one of the two findings is still open";
      explainEl.textContent = actionWild
        ? "Resource is scoped, but Action:\"*\" still means any operation — read, write, delete — "
          + "against that one resource. Scoping only the noun and not the verb isn't least privilege."
        : "Action is scoped, but Resource:\"*\" means that operation runs against every resource in the "
          + "account, not just the one this app needs.";
    } else {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "both wildcard findings closed";
      explainEl.textContent = hasCondition
        ? "Action and Resource are both scoped, and the Condition narrows it further (e.g. by prefix) — "
          + "the idea behind iam-policy-leastpriv.json, which uses two statements: s3:GetObject on app/* objects, "
          + "plus s3:ListBucket limited by an s3:prefix Condition."
        : "Action and Resource are both scoped — a Condition isn't required to close CWE-732/CWE-269, "
          + "but it's extra narrowing worth having when the resource itself allows it (e.g. a prefix).";
    }
  }

  PRESETS.forEach(function (p) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = p.label;
    b.addEventListener("click", function () { input.value = p.v; update(); });
    presetsEl.appendChild(b);
  });

  input.addEventListener("input", update);
  input.value = PRESETS[0].v;
  update();
})();
