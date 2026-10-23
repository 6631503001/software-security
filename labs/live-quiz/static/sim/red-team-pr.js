/* red-team-pr.js — Week 15 simulation.
 *
 * WHAT THIS IS FOR
 * gate-check answers one question: does a finding clear the HIGH,CRITICAL
 * filter? This sim answers the next one, the question a student asks in front
 * of a red Actions run: which JOB went red, at which STEP, and why the others
 * show green or "skipped". It lays out security-ci.yml's real three jobs and
 * every named step in order:
 *
 *   semgrep  : checkout -> scan->SARIF (|| true) -> upload (if: always()) -> Gate (--error)
 *   trivy    : checkout -> fs->SARIF (exit-code 0) -> upload -> config->SARIF -> upload
 *              -> Gate SCA (fs, scanners vuln,secret, exit-code 1) -> Gate IaC (config, exit-code 1)
 *   gitleaks : checkout (fetch-depth 0) -> scan->SARIF (--exit-code 0 || true) -> upload -> Gate (--exit-code 1)
 *
 * GitHub's step rule is applied as Actions applies it: a step with no `if:` runs
 * only while every earlier step succeeded, so after one gate fails the steps
 * after it are SKIPPED. The upload steps carry `if: always()` and come before the
 * gates anyway, so the SARIF always lands.
 *
 * WHAT EACH GATE FINDS: none of it is invented. Every row was produced on
 * 23 Oct 2026 by running each gate step's own command (the same flags as
 * security-ci.yml; Trivy 0.70.0, semgrep/semgrep:latest, zricethezav/gitleaks:latest)
 * against a throwaway repo laid out the way the worksheet asks (lab files plus
 * .github/workflows/security-ci.yml):
 *
 *   untouched      semgrep RED  (github-actions-mutable-action-tag x7 per workflow copy,
 *                                avoid_app_run_with_bad_host x2)   trivy fs/config green
 *                  gitleaks RED (curl-auth-header x3)
 *                  The untouched and urllib3 rows were also confirmed on real GitHub Actions.
 *   Blue fixes     all four gates exit 0
 *   + urllib3      trivy fs RED (requirements.txt, Total: 7 HIGH, e.g. CVE-2019-11324)
 *   + no USER      semgrep RED (missing-user) and trivy config RED (DS-0002 HIGH)
 *   + USER root    semgrep RED (last-user-is-root) and trivy config RED (DS-0002 HIGH)
 *   + ghp_ token   gitleaks RED (github-pat) and trivy fs RED (secret, CRITICAL, github-pat)
 *
 * Nothing is sent anywhere.
 */
(function () {
  "use strict";

  // --- what each gate command reports, per planted change (from the real runs) ---
  var RAW_SEMGREP = [
    "yaml.github-actions.security.github-actions-mutable-action-tag",
    "  security-ci.yml (both copies, 7 each): actions/checkout@v4 x3, github/codeql-action/upload-sarif@v3 x4",
    "python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host",
    "  insecure_service.py:56, secure_service.py:81   app.run(host=\"0.0.0.0\", ...)"
  ];
  var RAW_GITLEAKS = [
    "RuleID: curl-auth-header   README-pipeline.md:91",
    "RuleID: curl-auth-header   worksheet.md:59",
    "RuleID: curl-auth-header   worksheet.md:72",
    "  (the docs' own curl examples that send the toy alice-token header)"
  ];
  var DOCKER = {
    nouser: {
      semgrep: ["dockerfile.security.missing-user.missing-user", "  Dockerfile:6   CMD [\"python\", \"insecure_service.py\"]  (no USER before it)"],
      trivy: ["Dockerfile (dockerfile)  Failures: 1 (HIGH: 1, CRITICAL: 0)",
              "DS-0002 (HIGH): Specify at least 1 USER command in Dockerfile with non-root user as argument"]
    },
    root: {
      semgrep: ["dockerfile.security.last-user-is-root.last-user-is-root", "  Dockerfile:5   USER root"],
      trivy: ["Dockerfile (dockerfile)  Failures: 1 (HIGH: 1, CRITICAL: 0)",
              "DS-0002 (HIGH): Last USER command in Dockerfile should not be 'root'"]
    }
  };
  // Captured 2026-10-23; the count moves as the Trivy DB updates — grade the red gate, not the number.
  var DEP_TRIVY = ["requirements.txt (pip)  Total: 7 (HIGH: 7, CRITICAL: 0)   [captured 23 Oct 2026]",
                   "urllib3 1.24.1  CVE-2019-11324 HIGH  fixed in 1.24.2  (+6 more HIGH)"];
  var TOKEN_TRIVY = ["settings.py (secrets)  Total: 1 (HIGH: 0, CRITICAL: 1)",
                     "CRITICAL: GitHub (github-pat)  GitHub Personal Access Token"];
  var TOKEN_GITLEAKS = ["RuleID: github-pat   settings.py:2   GITHUB_TOKEN = \"ghp_…\""];

  // --- the workflow's jobs and steps, names exactly as in security-ci.yml ---
  var JOBS = [
    { id: "semgrep", name: "SAST (Semgrep)", steps: [
      { name: "Run actions/checkout@{ref}" },
      { name: "Semgrep scan -> SARIF", note: "|| true: never fails" },
      { name: "Upload Semgrep SARIF", always: true, note: "if: always()" },
      { name: "Gate — fail on Semgrep findings", gate: "semgrep", note: "--error: any finding fails" }
    ]},
    { id: "trivy", name: "SCA + IaC (Trivy)", steps: [
      { name: "Run actions/checkout@{ref}" },
      { name: "Trivy fs (SCA) -> SARIF", note: "exit-code \"0\": report only" },
      { name: "Upload Trivy fs SARIF", always: true, note: "if: always()" },
      { name: "Trivy config (IaC) -> SARIF", note: "exit-code \"0\": report only" },
      { name: "Upload Trivy config SARIF", always: true, note: "if: always()" },
      { name: "Gate — fail on HIGH/CRITICAL (SCA)", gate: "trivyfs", note: "fs, scanners: vuln,secret, HIGH,CRITICAL" },
      { name: "Gate — fail on HIGH/CRITICAL (IaC)", gate: "trivyconfig", note: "config, HIGH,CRITICAL" }
    ]},
    { id: "gitleaks", name: "Secrets (Gitleaks)", steps: [
      { name: "Run actions/checkout@{ref}", note: "fetch-depth: 0 (full history)" },
      { name: "Gitleaks scan -> SARIF", note: "--exit-code 0 || true" },
      { name: "Upload Gitleaks SARIF", always: true, note: "if: always()" },
      { name: "Gate — fail if any secret found", gate: "gitleaks", note: "--exit-code 1" }
    ]}
  ];

  var PRESETS = [
    { label: "untouched lab: why is it red already?", blue: false, dep: false, docker: "none", token: false },
    { label: "Blue's clean baseline", blue: true, dep: false, docker: "none", token: false },
    { label: "Red: old urllib3", blue: true, dep: true, docker: "none", token: false },
    { label: "Red: root Dockerfile", blue: true, dep: false, docker: "root", token: false },
    { label: "Red: hardcoded token", blue: true, dep: false, docker: "none", token: true },
    { label: "two defects in one PR", blue: true, dep: true, docker: "nouser", token: false }
  ];

  var startRaw = document.getElementById("start-raw");
  var startBlue = document.getElementById("start-blue");
  var depBox = document.getElementById("d-dep");
  var dockerSel = document.getElementById("d-docker");
  var tokenBox = document.getElementById("d-token");
  var presetsEl = document.getElementById("presets");
  var jobsEl = document.getElementById("jobs");
  var verdictEl = document.getElementById("verdict");
  var whyEl = document.getElementById("why");
  var sarifEl = document.getElementById("sarif");

  // What each gate command prints as findings for the current repo state.
  function findings(s) {
    var f = { semgrep: [], trivyfs: [], trivyconfig: [], gitleaks: [] };
    if (!s.blue) {
      f.semgrep = f.semgrep.concat(RAW_SEMGREP);
      f.gitleaks = f.gitleaks.concat(RAW_GITLEAKS);
    }
    if (s.docker !== "none") {
      f.semgrep = f.semgrep.concat(DOCKER[s.docker].semgrep);
      f.trivyconfig = f.trivyconfig.concat(DOCKER[s.docker].trivy);
    }
    if (s.dep) { f.trivyfs = f.trivyfs.concat(DEP_TRIVY); }
    if (s.token) {
      f.trivyfs = f.trivyfs.concat(TOKEN_TRIVY);
      f.gitleaks = f.gitleaks.concat(TOKEN_GITLEAKS);
    }
    return f;
  }

  // GitHub's rule: a step without if: runs only while nothing before it failed.
  function runJob(job, f) {
    var failed = false;
    return job.steps.map(function (st) {
      if (failed && !st.always) { return { st: st, state: "skipped" }; }
      if (st.gate && f[st.gate].length) { failed = true; return { st: st, state: "failure", log: f[st.gate] }; }
      return { st: st, state: "success" };
    });
  }

  var ICON = { success: "✓", failure: "✗", skipped: "⊘" };

  function renderJob(job, rows, ref) {
    var red = rows.some(function (r) { return r.state === "failure"; });
    var card = document.createElement("div");
    card.className = "card rt-job " + (red ? "rt-red" : "rt-green");
    var h = document.createElement("div");
    h.className = "rt-jobhead";
    var ic = document.createElement("span");
    ic.className = "rt-icon rt-" + (red ? "failure" : "success");
    ic.textContent = red ? ICON.failure : ICON.success;
    var nm = document.createElement("b");
    nm.textContent = job.name;
    h.appendChild(ic);
    h.appendChild(nm);
    card.appendChild(h);
    var ol = document.createElement("ol");
    ol.className = "rt-steps";
    rows.forEach(function (r) {
      var li = document.createElement("li");
      li.className = "rt-step rt-s-" + r.state;
      var i = document.createElement("span");
      i.className = "rt-icon rt-" + r.state;
      i.textContent = ICON[r.state];
      var t = document.createElement("span");
      t.className = "rt-stepname";
      t.textContent = r.st.name.replace("{ref}", ref);
      li.appendChild(i);
      li.appendChild(t);
      if (r.st.note) {
        var n = document.createElement("span");
        n.className = "rt-stepnote";
        n.textContent = r.state === "skipped" ? "skipped: an earlier step failed" : r.st.note;
        li.appendChild(n);
      }
      if (r.log) {
        var pre = document.createElement("div");
        pre.className = "rt-log";
        pre.textContent = r.log.join("\n") + "\nError: Process completed with exit code 1.";
        li.appendChild(pre);
      }
      ol.appendChild(li);
    });
    card.appendChild(ol);
    return { el: card, red: red };
  }

  function addWhy(text) {
    var li = document.createElement("li");
    li.textContent = text;
    whyEl.appendChild(li);
  }

  function update() {
    var s = { blue: startBlue.checked, dep: depBox.checked, docker: dockerSel.value, token: tokenBox.checked };
    var f = findings(s);
    jobsEl.textContent = "";
    var redJobs = [];
    var trivyRows = null;
    JOBS.forEach(function (job) {
      var rows = runJob(job, f);
      if (job.id === "trivy") { trivyRows = rows; }
      var r = renderJob(job, rows, s.blue ? "<commit SHA>" : "v4");
      if (r.red) { redJobs.push(job.name); }
      jobsEl.appendChild(r.el);
    });

    whyEl.textContent = "";
    var planted = s.dep || s.docker !== "none" || s.token;
    if (!redJobs.length) {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "All 3 jobs green: the PR can merge.";
      addWhy("This is Blue's Task 3 target. Every gate step ran and exited 0. Plant one defect to see which step catches it.");
    } else {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = redJobs.length + " of 3 jobs red: " + redJobs.join(", ") + ".";
    }
    if (!s.blue) {
      addWhy("The untouched lab is red before Red plants anything. Semgrep flags every @v4/@v3 action tag, "
        + "because a tag can be moved and a commit SHA can't. The trivy-action lines are already pinned to a SHA, "
        + "which is what passing looks like. Semgrep also flags host=\"0.0.0.0\". Gitleaks flags the docs' own curl "
        + "examples (curl-auth-header), a false positive. Clearing these with a reason is Task 3. "
        + "Switch to \"after Blue's fixes\" before you judge a Red defect.");
    }
    if (s.docker !== "none") {
      addWhy("One defect, two jobs: the root Dockerfile trips Trivy config (DS-0002, HIGH) and also Semgrep's "
        + "Dockerfile rule (" + (s.docker === "root" ? "last-user-is-root" : "missing-user")
        + "). Semgrep's --error gate has no severity filter.");
    }
    if (s.token) {
      addWhy("One defect, two jobs: Gitleaks catches the ghp_ token (github-pat), and so does Trivy. Its fs gate "
        + "runs scanners: vuln,secret, and a GitHub token is a CRITICAL secret finding.");
    }
    if (s.dep && !s.token) {
      addWhy("urllib3==1.24.1 is caught only by the Trivy SCA gate: 7 HIGH CVEs on 23 Oct 2026 (the count moves as "
        + "Trivy's database updates), e.g. CVE-2019-11324. Semgrep and "
        + "Gitleaks have nothing to say about a version number.");
    }
    var skipped = trivyRows.filter(function (r) { return r.state === "skipped" && r.st.gate; });
    if (skipped.length && f.trivyconfig.length) {
      addWhy("Inside the trivy job, the SCA gate failed first, so the IaC gate was SKIPPED and its DS-0002 verdict "
        + "never printed. This red run hides the second defect, which is why the worksheet asks for one defect "
        + "per PR.");
    }
    if (planted && !s.blue) {
      addWhy("With the baseline still red you can't tell which red came from Red's defect. Semgrep and Gitleaks "
        + "were red already.");
    }

    var all = ["semgrep", "trivyfs", "trivyconfig", "gitleaks"].reduce(function (n, k) { return n + (f[k].length ? 1 : 0); }, 0);
    sarifEl.textContent = "Security tab: all four SARIF uploads ran in every scenario, because they come before "
      + "the gates and carry if: always(). Every finding above is listed there"
      + (skipped.length && f.trivyconfig.length ? ", including the DS-0002 that the skipped gate never printed" : "")
      + ". The Trivy report steps upload every severity, because trivy-action drops the severity filter for SARIF "
      + "unless limit-severities-for-sarif is set. Only the gate steps filter to HIGH,CRITICAL."
      + (all ? "" : " (No findings in this scenario.)");
  }

  PRESETS.forEach(function (p) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = p.label;
    b.addEventListener("click", function () {
      if (p.blue) { startBlue.checked = true; } else { startRaw.checked = true; }
      depBox.checked = p.dep;
      dockerSel.value = p.docker;
      tokenBox.checked = p.token;
      update();
    });
    presetsEl.appendChild(b);
  });

  [startRaw, startBlue, depBox, dockerSel, tokenBox].forEach(function (el) {
    el.addEventListener("change", update);
  });
  update();
})();
