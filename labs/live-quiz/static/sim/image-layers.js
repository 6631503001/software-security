/* image-layers.js — Week 13 simulation.
 *
 * WHAT THIS IS FOR
 * Task 3 says the ENV secret is "exposed via docker history --no-trunc". Two
 * things students get wrong: they think the truncated view hides it (it shows
 * 30 of the token's 34 characters), and they think the secret sits in a file
 * layer you could delete later (the ENV rows are 0B — it is in the image
 * config that ships with every pull). This replays the real terminal output
 * for both lab images so they can see exactly where it shows up and where it
 * doesn't.
 *
 * WHERE THE DATA COMES FROM
 * Every line below is verbatim output captured on 2026-10-23 (Docker 29.6.1,
 * arm64) after
 *   docker build -f Dockerfile.insecure -t week13-insecure:lab .
 *   docker build -f Dockerfile.hardened -t week13-hardened:lab .
 * in labs/week13-cloud-container. Only the Dockerfile's own history rows are
 * listed; the base image's rows are folded into one line, and the CREATED
 * column is dropped (it is just a timestamp). Nothing is computed or fetched.
 */
(function () {
  "use strict";

  var SECRETS = [
    "sk_live_supersecret_DO_NOT_DO_THIS", "AKIAEXAMPLEdeadbeefdeadbeef",
    "sk_live_supersecret_DO_NOT_DO_", "AKIAEXAMPLEdeadbee"
  ];

  var IMG = {
    insecure: {
      name: "week13-insecure:lab",
      size: "1.65GB",
      // [CREATED BY (default, truncated), CREATED BY (--no-trunc), SIZE]
      history: [
        ["CMD [\"python\" \"app.py\"]", "CMD [\"python\" \"app.py\"]", "0B"],
        ["EXPOSE [5000/tcp]", "EXPOSE [5000/tcp]", "0B"],
        ["RUN /bin/sh -c chmod -R 777 /app # buildkit", "RUN /bin/sh -c chmod -R 777 /app # buildkit", "77.8kB"],
        ["RUN /bin/sh -c pip install -r requirements.t…", "RUN /bin/sh -c pip install -r requirements.txt # buildkit", "19.1MB"],
        ["COPY . . # buildkit", "COPY . . # buildkit", "77.8kB"],
        ["WORKDIR /app", "WORKDIR /app", "8.19kB"],
        ["ENV AWS_SECRET_ACCESS_KEY=AKIAEXAMPLEdeadbee…", "ENV AWS_SECRET_ACCESS_KEY=AKIAEXAMPLEdeadbeefdeadbeef", "0B"],
        ["ENV API_TOKEN=sk_live_supersecret_DO_NOT_DO_…", "ENV API_TOKEN=sk_live_supersecret_DO_NOT_DO_THIS", "0B"]
      ],
      base: "… 11 more rows from python:latest (Debian trixie; Python 3.15.1 that day) — not from this Dockerfile",
      env: ["PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHON_VERSION=3.15.1",
            "PYTHON_SHA256=673ae7232d84c894729882c8257d300ef2d26523911bfd3917ec8ce7f526f99b",
            "API_TOKEN=sk_live_supersecret_DO_NOT_DO_THIS",
            "AWS_SECRET_ACCESS_KEY=AKIAEXAMPLEdeadbeefdeadbeef"],
      user: "",
      ls: ["total 60",
           "drwxrwxrwx 1 root root  4096 Oct 22 19:00 .",
           "drwxr-xr-x 1 root root  4096 Oct 22 19:01 ..",
           "-rwxrwxrwx 1 root root  2965 Oct 22 18:57 Dockerfile.hardened",
           "-rwxrwxrwx 1 root root  1535 Oct 22 18:57 Dockerfile.insecure",
           "-rwxrwxrwx 1 root root  2297 Oct 22 18:57 README.md",
           "-rwxrwxrwx 1 root root   638 Oct 22 18:57 app.py",
           "-rwxrwxrwx 1 root root  2282 Oct 22 18:57 harden.md",
           "-rwxrwxrwx 1 root root   517 Oct 22 18:57 iam-policy-insecure.json",
           "-rwxrwxrwx 1 root root   844 Oct 22 18:57 iam-policy-leastpriv.json",
           "drwxrwxrwx 1 root root  4096 Oct 22 18:57 img",
           "-rwxrwxrwx 1 root root   278 Oct 22 18:57 requirements.txt",
           "-rwxrwxrwx 1 root root  2154 Oct 22 18:57 scan.sh",
           "-rwxrwxrwx 1 root root 10336 Oct 22 18:57 worksheet.md"]
    },
    hardened: {
      name: "week13-hardened:lab",
      size: "137MB",
      history: [
        ["CMD [\"app.py\"]", "CMD [\"app.py\"]", "0B"],
        ["EXPOSE [5000/tcp]", "EXPOSE [5000/tcp]", "0B"],
        ["USER 65532:65532", "USER 65532:65532", "0B"],
        ["ENV PATH=/venv/bin:/usr/local/sbin:/usr/loca…",
         "ENV PATH=/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin PYTHONPATH=/venv/lib/python3.11/site-packages", "0B"],
        ["COPY /app/app.py /app/app.py # buildkit", "COPY /app/app.py /app/app.py # buildkit", "12.3kB"],
        ["COPY /venv /venv # buildkit", "COPY /venv /venv # buildkit", "35.4MB"],
        ["WORKDIR /app", "WORKDIR /app", "8.19kB"]
      ],
      base: "… 43 more rows from gcr.io/distroless/python3-debian12 (bazel-built) — not from this Dockerfile",
      env: ["PATH=/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt",
            "LANG=C.UTF-8",
            "PYTHONPATH=/venv/lib/python3.11/site-packages"],
      user: "65532:65532",
      ls: ["docker: Error response from daemon: … error during container init:",
           "exec: \"ls\": executable file not found in $PATH"]
    }
  };

  var CMDS = [
    { id: "history", label: "docker history", cmd: function (n) { return "docker history " + n; } },
    { id: "notrunc", label: "docker history --no-trunc", cmd: function (n) { return "docker history --no-trunc " + n; } },
    { id: "env", label: "docker inspect … .Config.Env", cmd: function (n) { return "docker inspect --format '{{json .Config.Env}}' " + n; } },
    { id: "user", label: "docker inspect … .Config.User", cmd: function (n) { return "docker inspect --format '{{.Config.User}}' " + n; } },
    { id: "ls", label: "docker run … ls -la /app", cmd: function (n) { return "docker run --rm --entrypoint ls " + n + " -la /app"; } }
  ];

  var VERDICT = {
    insecure: {
      history: ["bad", "Truncated — and still leaking",
        "docker cuts CREATED BY at 45 characters for display. That still prints 30 of API_TOKEN's 34 characters "
        + "and the AKIA… key's first 18. Truncation is a column width, not protection."],
      notrunc: ["bad", "Both secrets, in full, in the two ENV rows",
        "This is the Task 3 command. Note the SIZE: 0B. The secret is not a file you could delete in a later layer — "
        + "it is in the image's config, which ships with every pull. The only fix is to rebuild without the ENV line "
        + "and rotate both keys."],
      env: ["bad", "No truncation at all — and every process inherits it",
        "The same config, as JSON. Anyone who can pull the image reads it, and every process started in the "
        + "container gets API_TOKEN and AWS_SECRET_ACCESS_KEY in its environment."],
      user: ["bad", "Empty User = the container runs as root",
        "No USER line, so .Config.User is blank and the process is uid 0 (docker run … id prints uid=0(root)). "
        + "This is the one DS-0002 flags."],
      ls: ["bad", "COPY . . shipped Dockerfile.insecure itself — secrets in a file too",
        "The whole build context came along: the Dockerfile with both secrets in plaintext, the IAM policies, the "
        + "worksheet. Every entry is rwxrwxrwx from chmod -R 777. Here the context is just the lab folder; at a real "
        + "repo root it would also sweep in .git and .env — no Trivy rule catches either."]
    },
    hardened: {
      history: ["ok", "No secret row — and no build stage either",
        "The pip install ran in the throw-away build stage, so it leaves no history row here: only COPY /venv /venv "
        + "arrives. The secret never appears because it was never written into the Dockerfile."],
      notrunc: ["ok", "Full output, nothing to hide",
        "The only ENV is PATH and PYTHONPATH. The token is injected at run time (a mounted secret, a secrets manager, "
        + "an orchestrator secret — harden.md row 2), so it never enters any layer or the config."],
      env: ["ok", "Nothing secret in the config",
        "Four ordinary variables. Whoever pulls this image learns where the venv is, not your keys."],
      user: ["ok", "65532:65532 — the distroless nonroot user",
        "This is how to prove non-root on a distroless image, since you cannot exec a shell into it to run id."],
      ls: ["ok", "There is no ls to run",
        "Distroless ships no shell and no coreutils. That is the point: code execution inside this container has "
        + "nothing to call. Use docker inspect (the .Config.User button) for evidence instead."]
    }
  };

  var imgIns = document.getElementById("img-insecure");
  var imgHard = document.getElementById("img-hardened");
  var cmdsEl = document.getElementById("cmds");
  var sizeEl = document.getElementById("size");
  var cmdlineEl = document.getElementById("cmdline");
  var outEl = document.getElementById("out");
  var verdictEl = document.getElementById("verdict");
  var explainEl = document.getElementById("explain");
  var current = "history";

  // Append text to a node, wrapping any known secret (longest match first) in
  // a highlight span. textContent only — no markup is ever parsed.
  function appendHighlighted(node, text) {
    var rest = text;
    while (rest.length) {
      var at = -1, hit = "";
      SECRETS.forEach(function (s) {
        var i = rest.indexOf(s);
        if (i !== -1 && (at === -1 || i < at || (i === at && s.length > hit.length))) { at = i; hit = s; }
      });
      if (at === -1) { node.appendChild(document.createTextNode(rest)); return; }
      if (at > 0) node.appendChild(document.createTextNode(rest.slice(0, at)));
      var mark = document.createElement("span");
      mark.className = "layers-secret";
      mark.textContent = hit;
      node.appendChild(mark);
      rest = rest.slice(at + hit.length);
    }
  }

  function row(text, cls) {
    var d = document.createElement("div");
    d.className = "layers-row" + (cls ? " " + cls : "");
    appendHighlighted(d, text);
    if (SECRETS.some(function (s) { return text.indexOf(s) !== -1; })) d.className += " is-leak";
    outEl.appendChild(d);
  }

  function pad(s, n) { while (s.length < n) s += " "; return s; }

  function render() {
    var key = imgHard.checked ? "hardened" : "insecure";
    var im = IMG[key];
    var c = CMDS.filter(function (x) { return x.id === current; })[0];

    Array.prototype.forEach.call(cmdsEl.querySelectorAll("button"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-cmd") === current ? "true" : "false");
    });

    cmdlineEl.textContent = "$ " + c.cmd(im.name);
    outEl.innerHTML = "";
    if (current === "history" || current === "notrunc") {
      var full = current === "notrunc";
      row(pad("CREATED BY", full ? 0 : 47) + (full ? "  " : "") + "SIZE", "is-head");
      im.history.forEach(function (h) {
        var cb = full ? h[1] : h[0];
        row(full ? cb + "  " + h[2] : pad(cb, 47) + h[2]);
      });
      row(im.base, "is-fold");
    } else if (current === "env") {
      row("[");
      im.env.forEach(function (e, i) { row("  \"" + e + "\"" + (i < im.env.length - 1 ? "," : "")); });
      row("]");
    } else if (current === "user") {
      row(im.user === "" ? "(empty line)" : im.user, im.user === "" ? "is-fold" : "");
    } else {
      im.ls.forEach(function (l) {
        row(l, l.indexOf("Dockerfile.insecure") !== -1 ? "is-leak" : "");
      });
    }

    var v = VERDICT[key][current];
    verdictEl.className = "verdict " + v[0];
    verdictEl.textContent = v[1];
    explainEl.textContent = v[2];
    sizeEl.textContent = "Image size (docker image ls): week13-insecure:lab " + IMG.insecure.size
      + " · week13-hardened:lab " + IMG.hardened.size;
  }

  CMDS.forEach(function (c) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "layers-btn";
    b.setAttribute("data-cmd", c.id);
    b.textContent = c.label;
    b.addEventListener("click", function () { current = c.id; render(); });
    cmdsEl.appendChild(b);
  });
  imgIns.addEventListener("change", render);
  imgHard.addEventListener("change", render);
  render();
})();
