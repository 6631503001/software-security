/* fail-open.js — Week 15 simulation.
 *
 * WHAT THIS IS FOR
 * "Fail open" stays abstract until a student sends one request to both of
 * this week's services and sees them disagree. This replays GET /admin
 * against the two real lab files side by side:
 *
 *   insecure_service.py :8090   user = USERS[token]      -> KeyError on an unknown/empty token
 *                               except Exception: return jsonify(panel="UNLOCKED", secret=SECRET)
 *                               (no security logger anywhere: A09)
 *   secure_service.py   :8091   user = USERS.get(token)  -> None, never raises
 *                               None -> security_log.warning(... reason=unauthenticated), 403
 *                               not admin -> security_log.warning(... reason=not_admin), 403
 *                               admin -> security_log.info(event=authz_success ...), 200
 *
 * The input space is finite (4 header choices x X-Forwarded-For on/off), so
 * instead of re-deriving the outputs in JavaScript this replays the real ones.
 * OUTCOMES below holds the status, body and security-log line that each service
 * returned. tests/test_content.py parses the block between the BEGIN/END markers
 * as JSON and checks every row against insecure_service.py and secure_service.py
 * run through Flask's test client. If the lab code drifts, CI goes red. The
 * werkzeug access-log lines were captured from the real containers
 * (docker compose up, then curl :8090 and :8091 with these exact headers), on
 * 23 Oct 2026. 192.168.65.1 is the Docker Desktop gateway that the containers
 * saw; on Linux it is usually 172.17.0.1 or 172.18.0.1.
 *
 * Nothing is sent anywhere.
 */
(function () {
  "use strict";

  // BEGIN OUTCOMES
  var OUTCOMES = {
    "insecure": {
      "none":        {"path": "keyerror",  "status": 200, "body": {"panel": "UNLOCKED", "secret": "<SECRET>"}, "log": null},
      "garbage":     {"path": "keyerror",  "status": 200, "body": {"panel": "UNLOCKED", "secret": "<SECRET>"}, "log": null},
      "alice-token": {"path": "admin",     "status": 200, "body": {"panel": "UNLOCKED", "secret": "<SECRET>"}, "log": null},
      "bob-token":   {"path": "not_admin", "status": 403, "body": {"error": "forbidden"}, "log": null}
    },
    "secure": {
      "none":        {"path": "unauth",    "status": 403, "body": {"error": "forbidden"},
                      "log": ["WARNING", "event=authz_failure outcome=deny src_ip={ip} reason=unauthenticated"]},
      "garbage":     {"path": "unauth",    "status": 403, "body": {"error": "forbidden"},
                      "log": ["WARNING", "event=authz_failure outcome=deny src_ip={ip} reason=unauthenticated"]},
      "alice-token": {"path": "admin",     "status": 200, "body": {"panel": "UNLOCKED", "secret": "<SECRET>"},
                      "log": ["INFO", "event=authz_success outcome=allow subject=alice src_ip={ip}"]},
      "bob-token":   {"path": "not_admin", "status": 403, "body": {"error": "forbidden"},
                      "log": ["WARNING", "event=authz_failure outcome=deny subject=bob src_ip={ip} reason=not_admin"]}
    }
  };
  // END OUTCOMES

  var PEER = "192.168.65.1";        // what request.remote_addr was inside the containers
  var SPOOF = "203.0.113.9";
  var FLAG_SHOWN = "FLAG{devsecops_…}";

  // The code each path walks through, quoted from the two lab files.
  // state: "ran" | "hot" (the line that decides) | "skip" (exists, not reached)
  var TRACES = {
    insecure: {
      keyerror: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS[token]", "raises KeyError: {tok} is not a key in USERS", "hot"],
        ["except Exception:", "the KeyError is caught here", "ran"],
        ["return jsonify(panel=\"UNLOCKED\", secret=SECRET)", "FAIL OPEN: grants access, and no security log line is written", "hot"]
      ],
      not_admin: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS[token]", "user = \"bob\" (a real key, so no exception)", "ran"],
        ["if user not in ADMINS:", "true, because bob is not an admin", "hot"],
        ["return jsonify(error=\"forbidden\"), 403", "denied, but no security log line is written", "ran"]
      ],
      admin: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS[token]", "user = \"alice\"", "ran"],
        ["if user not in ADMINS:", "false, because alice is an admin", "ran"],
        ["return jsonify(panel=\"UNLOCKED\", secret=SECRET)", "the legitimate unlock, with no security log line", "ran"]
      ]
    },
    secure: {
      unauth: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS.get(token)", "user = None (.get() returns None, it never raises)", "ran"],
        ["if user is None:", "true", "hot"],
        ["security_log.warning(\"event=authz_failure ... reason=unauthenticated\")", "logged on the security logger, without the token value", "ran"],
        ["return jsonify(error=\"forbidden\"), 403", "denied", "ran"]
      ],
      not_admin: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS.get(token)", "user = \"bob\"", "ran"],
        ["if user not in ADMINS:", "true, because bob is not an admin", "hot"],
        ["security_log.warning(\"event=authz_failure ... reason=not_admin\")", "logged with subject=bob", "ran"],
        ["return jsonify(error=\"forbidden\"), 403", "denied", "ran"]
      ],
      admin: [
        ["token = request.headers.get(\"Authorization\", \"\")", "token = {tok}", "ran"],
        ["user = USERS.get(token)", "user = \"alice\"", "ran"],
        ["if user not in ADMINS:", "false, because alice is an admin", "ran"],
        ["security_log.info(\"event=authz_success ...\")", "successes are logged too", "ran"],
        ["return jsonify(panel=\"UNLOCKED\", secret=SECRET)", "the legitimate unlock", "ran"]
      ]
    }
  };
  var SECURE_EXCEPT = ["except Exception as exc:",
    "never reached with any header. .get() can't raise, so this is only the safety net (deny + event=authz_error)", "skip"];

  var PRESETS = [
    { label: "no token (the attack)", token: "none", xff: false },
    { label: "made-up token", token: "garbage", xff: false },
    { label: "real admin", token: "alice-token", xff: false },
    { label: "user, not admin", token: "bob-token", xff: false },
    { label: "spoofed source IP", token: "none", xff: true }
  ];

  var tokenSel = document.getElementById("token");
  var xffBox = document.getElementById("xff");
  var presetsEl = document.getElementById("presets");
  var verdictEl = document.getElementById("verdict");
  var explainEl = document.getElementById("explain");
  var noteEl = document.getElementById("note");

  function pad(n, w) { var s = String(n); while (s.length < (w || 2)) { s = "0" + s; } return s; }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

  // The two timestamp formats the containers print (they run in UTC):
  //   logging asctime   2026-10-23 01:02:03,456
  //   werkzeug          [23/Oct/2026 01:02:03]
  function stamps() {
    var d = new Date();
    var hms = pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) + ":" + pad(d.getUTCSeconds());
    return {
      asc: d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()) + " " + hms
           + "," + pad(d.getUTCMilliseconds(), 3),
      wz: "[" + pad(d.getUTCDate()) + "/" + MON[d.getUTCMonth()] + "/" + d.getUTCFullYear() + " " + hms + "]"
    };
  }

  function bodyText(body) {
    var shown = {};
    Object.keys(body).forEach(function (k) {
      shown[k] = body[k] === "<SECRET>" ? FLAG_SHOWN : body[k];
    });
    return JSON.stringify(shown);
  }

  function addLine(el, text, cls) {
    var div = document.createElement("div");
    div.className = "fo-logline" + (cls ? " " + cls : "");
    div.textContent = text;
    el.appendChild(div);
  }

  function addStep(ol, step, tok) {
    var li = document.createElement("li");
    li.className = "fo-step fo-" + step[2];
    var c = document.createElement("code");
    c.textContent = step[0];
    var n = document.createElement("span");
    n.className = "fo-why";
    n.textContent = step[1].replace("{tok}", tok);
    li.appendChild(c);
    li.appendChild(n);
    ol.appendChild(li);
  }

  function renderPane(svc, key, xff, ts) {
    var o = OUTCOMES[svc][key];
    var statusEl = document.getElementById("status-" + svc);
    var bodyEl = document.getElementById("body-" + svc);
    var traceEl = document.getElementById("trace-" + svc);
    var logEl = document.getElementById("log-" + svc);
    var granted = o.status === 200;

    statusEl.textContent = o.status + (granted ? " OK" : " FORBIDDEN");
    statusEl.className = "fo-status " + (granted ? (key === "alice-token" ? "fo-allow" : "fo-leak") : "fo-deny");
    bodyEl.textContent = bodyText(o.body);

    var tok = key === "none" ? "\"\" (header missing)" : "\"" + key + "\"";
    traceEl.textContent = "";
    TRACES[svc][o.path].forEach(function (s) { addStep(traceEl, s, tok); });
    if (svc === "secure") { addStep(traceEl, SECURE_EXCEPT, tok); }

    logEl.textContent = "";
    var ip = xff ? SPOOF : PEER;
    var access = PEER + " - - " + ts.wz + " \"GET /admin HTTP/1.1\" " + o.status + " -";
    if (svc === "insecure") {
      // No logging config at all: only werkzeug's own access line reaches stderr.
      addLine(logEl, access, granted && key !== "alice-token" ? "fo-quiet" : "");
    } else {
      addLine(logEl, ts.asc + " level=" + o.log[0] + " logger=security " + o.log[1].replace("{ip}", ip),
              o.log[0] === "WARNING" ? "fo-alert" : "fo-info");
      addLine(logEl, ts.asc + " level=INFO logger=werkzeug " + access, "");
    }
  }

  function update() {
    var key = tokenSel.value;
    var xff = xffBox.checked;
    var ts = stamps();
    renderPane("insecure", key, xff, ts);
    renderPane("secure", key, xff, ts);

    if (key === "none" || key === "garbage") {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = ":8090 fails open. It hands the admin panel to a request with "
        + (key === "none" ? "no token at all" : "a token nobody issued") + ", and logs it as an ordinary 200.";
      explainEl.textContent = "USERS[token] raises KeyError, and the except branch returns the panel instead of "
        + "denying (A10 / CWE-636). :8091 has the same try/except shape but looks the token up with .get(), so the "
        + "same request is a 403 plus a WARNING on the security logger. That is the line a SIEM can alert on (A09). "
        + "On :8090 the attack leaves only a 200 access line, the same line alice's real admin request leaves.";
    } else if (key === "alice-token") {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "Both unlock. On the happy path the two services behave the same.";
      explainEl.textContent = "A real admin token gets the panel on both ports. This is why the auto-grader also "
        + "checks that alice-token still works after you harden: a fix that denies everyone fails as well. Testing "
        + "with valid tokens can't tell these two services apart.";
    } else {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "Both deny. Even the insecure service gets this one right.";
      explainEl.textContent = "bob-token is a real key in USERS, so USERS[token] doesn't raise and the explicit "
        + "'not in ADMINS' check returns 403. The fail-open bug sits only on the error path, which a missing or "
        + "unknown token reaches. :8091 also writes subject=bob reason=not_admin. :8090 writes nothing except the "
        + "access line.";
    }
    var notes = [];
    if (xff) {
      notes.push("X-Forwarded-For is on. :8091's security line now says src_ip=" + SPOOF + ", copied from a header "
        + "the client controls (_client_ip() trusts it). The werkzeug line still shows the real peer, " + PEER
        + ". A log is only as trustworthy as its inputs. :8090 doesn't read the header at all.");
    }
    if (OUTCOMES.insecure[key].status === 200 || OUTCOMES.secure[key].status === 200) {
      notes.push("The secret is shortened here. A local run returns the public demo value from the source code, "
        + "and your graded flag comes only from your hosted instance.");
    }
    noteEl.textContent = notes.join(" ");
  }

  PRESETS.forEach(function (p) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = p.label;
    b.addEventListener("click", function () {
      tokenSel.value = p.token;
      xffBox.checked = p.xff;
      update();
    });
    presetsEl.appendChild(b);
  });

  tokenSel.addEventListener("change", update);
  xffBox.addEventListener("change", update);
  update();
})();
