/* trivy-blindspot.js — Week 13 simulation.
 *
 * WHAT THIS IS FOR
 * The lab's real lesson is that `trivy config` flags only 3 of the 6 planted
 * defects in Dockerfile.insecure. Students hear "3 of 6" and still read a
 * 0-finding scan as "the image is clean". Here they fix the defects one at a
 * time and watch the scanner go to 0 while three defects are still in the file.
 *
 * WHERE THE LOGIC COMES FROM
 * - The insecure lines are verbatim from Dockerfile.insecure; each fix is the
 *   matching line from Dockerfile.hardened (harden.md rows 1-6). The one extra
 *   state, "python:3.11-slim" (a tag with no digest), is the what-if harden.md
 *   row 1 warns about.
 * - The rule model was checked against Trivy 0.76.1 (`aquasec/trivy:latest`,
 *   2026-10-23) scanning all 96 combinations of these toggles, 0 mismatches:
 *     DS-0001 MEDIUM   iff FROM is python:latest  (a bare tag passes!)
 *     DS-0002 HIGH     iff there is no non-root USER
 *     DS-0031 CRITICAL once per secret ENV line  (two lines -> two findings)
 *     DS-0026 LOW      always (no HEALTHCHECK) — hidden by --severity MEDIUM,HIGH,CRITICAL
 *   COPY . ., chmod -R 777 and the unpinned pip install never fire a rule.
 * - All six defects on = 4 findings (MEDIUM 1, HIGH 1, CRITICAL 2); all fixed =
 *   0, the same counts the lesson plan records for scan.sh.
 */
(function () {
  "use strict";

  var DIGEST = "python:3.11-slim@sha256:cdbd05fb6f457ca275ff51ce00d93d865ca0b6a25f5ffb08262d94f6835771e5";
  var FROM_LINE = {
    latest: "FROM python:latest",
    tag: "FROM python:3.11-slim",
    digest: "FROM " + DIGEST
  };
  var ENV_LINES = [
    { line: "ENV API_TOKEN=sk_live_supersecret_DO_NOT_DO_THIS", name: "API_TOKEN" },
    { line: "ENV AWS_SECRET_ACCESS_KEY=AKIAEXAMPLEdeadbeefdeadbeef", name: "AWS_SECRET_ACCESS_KEY" }
  ];
  var COPY_BAD = ["COPY . ."];
  var COPY_FIX = ["COPY requirements.txt .", "COPY app.py ."];
  var PIP_BAD = ["RUN pip install -r requirements.txt"];
  var PIP_FIX = ["RUN python -m venv /venv \\", "    && /venv/bin/pip install --no-cache-dir -r requirements.txt"];
  var CHMOD_BAD = "RUN chmod -R 777 /app";
  var USER_FIX = "USER 65532:65532";

  // The three defects no Trivy Dockerfile rule checks, plus the tag-without-digest case.
  var MANUAL = {
    tag: { row: 1, text: "FROM python:3.11-slim — DS-0001 only rejects :latest, so a bare tag passes. "
      + "A tag can be repointed tomorrow; harden.md row 1 asks for an @sha256 digest.", cwe: "CWE-1104" },
    copy: { row: 3, text: "COPY . . — drags the whole build context in (in this lab that includes "
      + "Dockerfile.insecure itself, secrets and all).", cwe: "CWE-538" },
    chmod: { row: 4, text: "RUN chmod -R 777 /app — any process in the container can rewrite the code.", cwe: "CWE-732" },
    pip: { row: 6, text: "RUN pip install -r requirements.txt — unpinned, as root, no --no-cache-dir.", cwe: "CWE-1104" }
  };

  var PRESETS = [
    { label: "Dockerfile.insecure (all 6)", s: { from: "latest", env: false, copy: false, chmod: false, user: false, pip: false } },
    { label: "fix only what Trivy flags", s: { from: "digest", env: true, copy: false, chmod: false, user: true, pip: false } },
    { label: "a tag, not a digest", s: { from: "tag", env: true, copy: true, chmod: true, user: true, pip: true } },
    { label: "all 6 fixed (= hardened)", s: { from: "digest", env: true, copy: true, chmod: true, user: true, pip: true } }
  ];

  var el = function (id) { return document.getElementById(id); };
  var fromSel = el("d-from"), envCb = el("d-env"), copyCb = el("d-copy"), chmodCb = el("d-chmod");
  var userCb = el("d-user"), pipCb = el("d-pip"), lowCb = el("d-low");
  var fileEl = el("file"), cmdEl = el("cmd"), sumEl = el("summary"), findEl = el("findings");
  var manualEl = el("manual"), verdictEl = el("verdict"), explainEl = el("explain"), presetsEl = el("presets");

  function state() {
    return { from: fromSel.value, env: envCb.checked, copy: copyCb.checked, chmod: chmodCb.checked,
             user: userCb.checked, pip: pipCb.checked, low: lowCb.checked };
  }

  // Assemble the file in Dockerfile.insecure's own line order. Each entry
  // remembers which harden.md row it belongs to and how Trivy treats it.
  function build(s) {
    var L = [];
    L.push({ t: FROM_LINE[s.from], kind: s.from === "latest" ? "flag" : (s.from === "tag" ? "manual" : "fixed"),
             tag: s.from === "latest" ? "DS-0001" : (s.from === "tag" ? "manual" : "") });
    if (!s.env) {
      ENV_LINES.forEach(function (e) { L.push({ t: e.line, kind: "flag", tag: "DS-0031" }); });
    }
    L.push({ t: "WORKDIR /app", kind: "plain", tag: "" });
    (s.copy ? COPY_FIX : COPY_BAD).forEach(function (t) {
      L.push({ t: t, kind: s.copy ? "fixed" : "manual", tag: s.copy ? "" : "manual" });
    });
    (s.pip ? PIP_FIX : PIP_BAD).forEach(function (t) {
      L.push({ t: t, kind: s.pip ? "fixed" : "manual", tag: s.pip ? "" : "manual" });
    });
    if (!s.chmod) L.push({ t: CHMOD_BAD, kind: "manual", tag: "manual" });
    L.push({ t: "EXPOSE 5000", kind: "plain", tag: "" });
    // No USER line at all is the defect, so show where it is missing. A ghost
    // row has no line number: it is not in the file Trivy reads.
    L.push(s.user ? { t: USER_FIX, kind: "fixed", tag: "" }
                  : { t: "(no USER line — runs as root, uid 0)", kind: "flag", tag: "DS-0002", ghost: true });
    L.push({ t: "CMD [\"python\", \"app.py\"]", kind: "plain", tag: "" });
    return L;
  }

  // Trivy's verdict for that file, in the order Trivy prints it (by rule ID).
  function scan(s) {
    var f = [];
    if (s.from === "latest") {
      f.push({ id: "DS-0001", sev: "MEDIUM", msg: "Specify a tag in the 'FROM' statement for image 'python'", line: 1 });
    }
    if (!s.user) {
      f.push({ id: "DS-0002", sev: "HIGH", msg: "Specify at least 1 USER command in Dockerfile with non-root user as argument", line: null });
    }
    if (s.low) {
      f.push({ id: "DS-0026", sev: "LOW", msg: "Add HEALTHCHECK instruction in your Dockerfile", line: null });
    }
    if (!s.env) {
      ENV_LINES.forEach(function (e, i) {
        f.push({ id: "DS-0031", sev: "CRITICAL", msg: "Possible exposure of secret env \"" + e.name + "\" in ENV", line: 2 + i });
      });
    }
    return f;
  }

  function manualOpen(s) {
    var m = [];
    if (s.from === "tag") m.push(MANUAL.tag);
    if (!s.copy) m.push(MANUAL.copy);
    if (!s.chmod) m.push(MANUAL.chmod);
    if (!s.pip) m.push(MANUAL.pip);
    return m;
  }

  function span(cls, text) {
    var x = document.createElement("span");
    x.className = cls;
    x.textContent = text;
    return x;
  }

  function render() {
    var s = state();
    var lines = build(s);
    var found = scan(s);
    var manual = manualOpen(s);

    fileEl.innerHTML = "";
    var n = 0;
    lines.forEach(function (ln) {
      var row = document.createElement("div");
      row.className = "trivyb-line is-" + ln.kind + (ln.ghost ? " is-ghost" : "");
      row.appendChild(span("trivyb-no", ln.ghost ? "" : String(++n)));
      row.appendChild(span("trivyb-src", ln.t));
      if (ln.tag) row.appendChild(span("trivyb-tag", ln.tag));
      fileEl.appendChild(row);
    });

    cmdEl.textContent = s.low ? "$ trivy config /src" : "$ trivy config --severity MEDIUM,HIGH,CRITICAL /src";
    var c = { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 };
    found.forEach(function (f) { c[f.sev] += 1; });
    var total = found.length;
    sumEl.textContent = "Failures: " + total + " ("
      + (s.low ? "UNKNOWN: 0, LOW: " + c.LOW + ", " : "")
      + "MEDIUM: " + c.MEDIUM + ", HIGH: " + c.HIGH + ", CRITICAL: " + c.CRITICAL + ")";
    sumEl.className = "trivyb-sum " + (total ? "is-bad" : "is-zero");

    findEl.innerHTML = "";
    if (!total) {
      findEl.appendChild(span("trivyb-none", "no misconfigurations — the scanner is satisfied"));
    }
    found.forEach(function (f) {
      var d = document.createElement("div");
      d.className = "trivyb-find sev-" + f.sev.toLowerCase();
      d.appendChild(span("trivyb-id", f.id + " (" + f.sev + ")"));
      d.appendChild(span("trivyb-msg", f.msg + (f.line ? "  — line " + f.line : "")));
      findEl.appendChild(d);
    });

    manualEl.innerHTML = "";
    if (!manual.length) {
      manualEl.appendChild(span("trivyb-none", "nothing left for a human to catch"));
    }
    manual.forEach(function (m) {
      var d = document.createElement("div");
      d.className = "trivyb-man";
      d.appendChild(span("trivyb-id", "row " + m.row + " · " + m.cwe));
      d.appendChild(span("trivyb-msg", m.text));
      manualEl.appendChild(d);
    });

    // DS-0026 is noise in this lab (scan.sh): judge "clean" on the filtered count.
    var real = found.filter(function (f) { return f.sev !== "LOW"; }).length;
    var low = total - real;
    var lowNote = low ? " (The LOW DS-0026 — no HEALTHCHECK — fires on every file, Dockerfile.hardened included; "
      + "scan.sh filters it out because it is none of the six defects.)" : "";
    if (real && manual.length) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = real + " finding" + (real > 1 ? "s" : "") + " — and " + manual.length
        + " more defect" + (manual.length > 1 ? "s" : "") + " Trivy will never report";
      explainEl.textContent = (!s.env ? "DS-0031 fires once per secret ENV line, so one defect counts twice. " : "")
        + "Your Task 1 table still needs a row for each defect on the left: rule ID where one fired, "
        + "\"manual review — no Trivy rule\" where none did." + lowNote;
    } else if (real) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = real + " finding" + (real > 1 ? "s" : "") + ", every remaining defect is one Trivy can see";
      explainEl.textContent = "Only rule-backed defects are left. Fix them and this scan really does reach 0." + lowNote;
    } else if (manual.length) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = (low ? "Only the LOW noise fires" : "Trivy says 0") + " — but " + manual.length
        + " defect" + (manual.length > 1 ? "s are" : " is") + " still in the file";
      var why = [];
      if (!s.copy || !s.chmod || !s.pip) why.push("no rule checks COPY scope, file permissions or install pinning");
      if (s.from === "tag") why.push("DS-0001 is happy with any tag that isn't :latest");
      explainEl.textContent = "This is the trap the lab is built around: a clean scan is not a clean image — "
        + why.join(", and ") + ". Only reading the Dockerfile finds " + (manual.length > 1 ? "these." : "this.") + lowNote;
    } else {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "0 findings and nothing left to catch by hand";
      explainEl.textContent = "Same shape as Dockerfile.hardened, which scan.sh scores 0. Task 4 asks you to prove "
        + "this with the before/after count — 4 → 0 — plus one sentence per fix." + lowNote;
    }
  }

  function apply(p) {
    fromSel.value = p.from;
    envCb.checked = p.env; copyCb.checked = p.copy; chmodCb.checked = p.chmod;
    userCb.checked = p.user; pipCb.checked = p.pip;
    render();
  }

  PRESETS.forEach(function (p) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = p.label;
    b.addEventListener("click", function () { apply(p.s); });
    presetsEl.appendChild(b);
  });

  [fromSel, envCb, copyCb, chmodCb, userCb, pipCb, lowCb].forEach(function (x) {
    x.addEventListener("change", render);
  });
  render();
})();
