/* llm-output.js — Week 14 simulation (LLM05 Improper Output Handling, worksheet Task 2).
 *
 * WHAT THIS IS FOR
 * "Treat the model's output as untrusted" stays abstract until a student watches
 * the SAME reply turn into code on one page and into harmless text on the other.
 * For one message this runs BOTH of this week's real chatbots side by side and
 * shows, per bot:
 *   1. which branch of the real code produced the reply,
 *   2. the exact bytes PAGE.format(reply=...) puts inside the reply <div>,
 *   3. what a browser's HTML parser builds from those bytes: what would run as
 *      script, what is merely injected markup, and what stays plain text.
 *
 * prompt-guard (the other W14 sim) walks the guardrail layers one at a time;
 * this one is only about the last hop — reply -> HTML -> browser.
 *
 * Logic copied from labs/week14-ai-llm-security/:
 *   vulnerable_chatbot.py  mock_llm(): injection_phrases (8 substrings, checked
 *                          FIRST) -> "hello"/"hi" substring greeting -> echo
 *                          f"You said: {user}". chat(): PAGE.format(reply=reply),
 *                          no escaping.
 *   guarded_chatbot.py     chat(): input_guardrail() (_INJECTION_RE) refuses ->
 *                          else mock_llm() (greeting / echo only) ->
 *                          redact_secret(); then escape() on EVERY reply.
 *   escape() is Python's html.escape(quote=True): & < > " ' become
 *   &amp; &lt; &gt; &quot; &#x27; — in that order.
 *
 * Step 3 uses the browser's own parser (DOMParser) on an inert document: nothing
 * in it executes or loads, and this page's CSP would block inline handlers
 * anyway. "Would run" is a reading of the parsed tree, not an execution.
 * tests/test_content.py checks both lists below against the two .py files.
 */
(function () {
  "use strict";

  // Both bots fall back to this when FLAG_PROMPTINJ is unset (the local default).
  var SECRET = "FLAG{pr0mpt_1nj3ction_l34ks_s3cr3ts}";

  // vulnerable_chatbot.py, mock_llm(): injection_phrases — verbatim.
  var INJECTION_PHRASES = [
    "ignore previous instructions",
    "ignore all previous",
    "reveal the secret",
    "print the secret",
    "what is the password",
    "show me the password",
    "repeat the system prompt",
    "tell me the secret"
  ];

  // guarded_chatbot.py: re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
  var INJECTION_RE = /ignore (all |the )?previous|ignore .* instructions|reveal|print|show|tell .* (secret|password)|what is the (secret|password)|repeat the system prompt|system prompt/i;

  var GREETING = "Hello! I'm HelpBot. How can I help you today?";
  var REFUSAL = "I can't help with that request.";
  // The reply <div> from both files' PAGE template.
  var DIV_OPEN = "<div style=\"border:1px solid #ccc;padding:8px;margin-top:8px\">";
  var DIV_CLOSE = "</div>";

  var PRESETS = [
    { label: "Task 2: script tag", v: "<script>alert(1)</script>" },
    { label: "Task 2: img onerror", v: "<img src=x onerror=alert(1)>" },
    { label: "payload says 'hi'", v: "<img src=x onerror=alert('hi')>" },
    { label: "onerror=print()", v: "<img src=x onerror=print()>" },
    { label: "markup, no script", v: "<h2>Session expired</h2><a href=//evil.test>Log in again</a>" }
  ];

  function pyEscape(s) {
    return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
  }

  function hasGreeting(low) {
    return low.indexOf("hello") !== -1 || low.indexOf("hi") !== -1;
  }

  // The word around the first "hi", so the student can see where it hid.
  function hiWord(msg) {
    var i = msg.toLowerCase().indexOf("hi");
    var a = i, b = i + 2;
    while (a > 0 && /[A-Za-z]/.test(msg.charAt(a - 1))) { a--; }
    while (b < msg.length && /[A-Za-z]/.test(msg.charAt(b))) { b++; }
    return msg.slice(a, b);
  }

  function runVulnerable(msg) {
    var low = msg.toLowerCase();
    for (var i = 0; i < INJECTION_PHRASES.length; i++) {
      if (low.indexOf(INJECTION_PHRASES[i]) !== -1) {
        return { branch: "leak", hit: INJECTION_PHRASES[i],
                 reply: "Sure! The secret password is " + SECRET + "." };
      }
    }
    if (hasGreeting(low)) { return { branch: "greet", reply: GREETING }; }
    return { branch: "echo", reply: "You said: " + msg };
  }

  function runGuarded(msg) {
    var m = INJECTION_RE.exec(msg);
    if (m) { return { branch: "refused", hit: m[0], reply: REFUSAL }; }
    var raw = hasGreeting(msg.toLowerCase()) ? GREETING : "You said: " + msg;
    var red = raw.split(SECRET).join("[REDACTED]");
    return { branch: raw === GREETING ? "greet" : "echo", redacted: red !== raw, reply: red };
  }

  // ---- what the browser's parser builds from the bytes ----
  var parser = new DOMParser();

  function handlerNote(name) {
    if (name === "onerror") { return "fires when loading fails — a bogus src like x fails at once, no click needed"; }
    if (name === "onload") { return "fires as soon as it loads — no click needed"; }
    return "fires when the reader triggers “" + name.slice(2) + "”";
  }

  function walk(node, effects, visible) {
    for (var c = node.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 3) { visible.push(c.nodeValue); continue; }
      if (c.nodeType !== 1) { continue; }
      var tag = c.tagName.toLowerCase();
      var label = "<" + tag + ">";
      if (tag === "script") {
        effects.push({ kind: "run", label: label + " element",
                       note: "runs as soon as the page loads: " + c.textContent });
        continue;
      }
      var ran = false;
      for (var i = 0; i < c.attributes.length; i++) {
        var n = c.attributes[i].name.toLowerCase();
        var v = c.attributes[i].value;
        if (n.indexOf("on") === 0) {
          effects.push({ kind: "run", label: label + " " + n + "=", note: handlerNote(n) + ": " + v });
          ran = true;
        } else if (/^\s*javascript:/i.test(v)) {
          effects.push({ kind: "run", label: label + " " + n + "=", note: "runs when clicked: " + v });
          ran = true;
        }
      }
      if (!ran) {
        effects.push({ kind: "markup", label: label + " element",
                       note: "real page markup the attacker added — no script, but they now control what the page shows" });
      }
      if (tag !== "style") { walk(c, effects, visible); }
    }
  }

  function parse(bytes) {
    var doc = parser.parseFromString(bytes, "text/html");
    var effects = [], visible = [];
    walk(doc.body, effects, visible);
    return { effects: effects, visible: visible.join("") };
  }

  // ---- rendering ----
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) { e.className = cls; }
    if (text !== undefined) { e.textContent = text; }
    return e;
  }

  // Show the bytes with tags and entities picked out (text nodes only).
  function showBytes(box, reply) {
    box.textContent = "";
    box.appendChild(el("span", "llm-output-dim", DIV_OPEN));
    var parts = reply.split(/(<[^>]*>|&[#A-Za-z0-9]+;)/);
    for (var i = 0; i < parts.length; i++) {
      if (!parts[i]) { continue; }
      var cls = "";
      if (parts[i].charAt(0) === "<") { cls = "llm-output-tag"; }
      else if (parts[i].charAt(0) === "&" && parts[i].charAt(parts[i].length - 1) === ";") { cls = "llm-output-ent"; }
      box.appendChild(el("span", cls, parts[i]));
    }
    box.appendChild(el("span", "llm-output-dim", DIV_CLOSE));
  }

  function showColumn(prefix, res, bytes, msg) {
    var branchEl = document.getElementById(prefix + "-branch");
    var bytesEl = document.getElementById(prefix + "-bytes");
    var domEl = document.getElementById(prefix + "-dom");
    var seenEl = document.getElementById(prefix + "-seen");
    var verdictEl = document.getElementById(prefix + "-verdict");
    var explainEl = document.getElementById(prefix + "-explain");

    var guarded = prefix === "g";
    var branchText = {
      leak: "mock_llm(): injection_phrases hit “" + res.hit + "” → fixed leak sentence",
      greet: "mock_llm(): \"hello\"/\"hi\" in the message → greeting",
      // guarded mock_llm() has no phrase list at all — only greeting / echo.
      echo: "mock_llm(): " + (guarded ? "" : "no phrase, ") + "no greeting → return f\"You said: {user}\"",
      refused: "input_guardrail(): _INJECTION_RE matched “" + res.hit + "” → refused, mock_llm() never ran"
    }[res.branch];
    if (guarded && res.branch !== "refused") { branchText = "input_guardrail(): no match → " + branchText; }
    if (guarded) {
      branchText += res.redacted ? " → redact_secret() replaced the flag" : "";
      branchText += " → escape()";
    } else {
      branchText += " → PAGE.format(reply=reply), no escaping";
    }
    branchEl.textContent = branchText;

    showBytes(bytesEl, bytes);

    var p = parse(bytes);
    domEl.textContent = "";
    if (!p.effects.length) {
      domEl.appendChild(el("div", "llm-output-node is-text", "one text node — no elements were created"));
    }
    p.effects.forEach(function (fx) {
      var row = el("div", "llm-output-node is-" + fx.kind);
      row.appendChild(el("span", "llm-output-nodelbl", fx.label));
      row.appendChild(el("span", "llm-output-nodeval", fx.note));
      domEl.appendChild(row);
    });
    seenEl.textContent = p.visible || "(nothing visible as text)";

    var runs = p.effects.some(function (f) { return f.kind === "run"; });
    var markup = p.effects.some(function (f) { return f.kind === "markup"; });
    var hasTag = msg.indexOf("<") !== -1;

    if (runs) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = "script runs in the reader’s browser — XSS (LLM05)";
    } else if (markup) {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = "no script, but the attacker rewrote the page (HTML injection — still LLM05)";
    } else if (res.branch === "leak") {
      verdictEl.className = "verdict bad";
      verdictEl.textContent = "no script — but the secret is on the page (that’s Task 1: LLM01→LLM02)";
    } else {
      verdictEl.className = "verdict ok";
      verdictEl.textContent = "plain text — nothing runs";
    }

    var why;
    if (res.branch === "leak") {
      why = "injection_phrases is checked before anything else, so the fixed leak sentence comes back and "
        + "your markup is never echoed at all.";
    } else if (res.branch === "greet") {
      why = msg.toLowerCase().indexOf("hello") !== -1
        ? "The message contains “hello”, so mock_llm() greets instead of echoing — the payload never reaches the page."
        : "The message contains “hi”"
          + (hiWord(msg).toLowerCase() === "hi" ? "" : " (inside “" + hiWord(msg) + "”)")
          + ", so mock_llm() took the greeting "
          + "branch — the payload never reaches the page. Same in the real lab: drop the “hi” to get the echo.";
    } else if (res.branch === "refused") {
      why = hasTag
        ? "The guardrail looks for phrases, not HTML: it refused because of the word “" + res.hit + "”, "
          + "not because of the tag. Remove that word and escape() is what has to save you."
        : "One of the 6 regex patterns matched, so there was no reply to render.";
    } else if (!guarded) {
      why = "The echo is dropped into PAGE.format(reply=reply) exactly as typed. The browser cannot tell the "
        + "model’s words from the page’s own HTML, so every tag in the reply becomes real markup.";
    } else {
      why = (res.redacted ? "redact_secret() swapped the flag for [REDACTED] first. " : "")
        + (hasTag
          ? "The guardrail did not stop this (it only knows phrases). escape() did: every < and > became an entity, "
            + "so the parser makes one text node and the reader sees the tag as characters."
          : "escape() runs on every reply; with nothing special in it, the text is unchanged on screen.");
    }
    explainEl.textContent = why;
  }

  var input = document.getElementById("msg");
  var presetsEl = document.getElementById("presets");
  var urlV = document.getElementById("url-v");
  var urlG = document.getElementById("url-g");

  function update() {
    var msg = input.value;
    var q = encodeURIComponent(msg);
    urlV.textContent = "http://localhost:8082/?msg=" + q;
    urlG.textContent = "http://localhost:8083/?msg=" + q;
    if (!msg) {
      ["v", "g"].forEach(function (p) {
        ["branch", "bytes", "dom", "seen", "verdict", "explain"].forEach(function (k) {
          document.getElementById(p + "-" + k).textContent = "";
        });
      });
      return;
    }
    var v = runVulnerable(msg);
    showColumn("v", v, v.reply, msg);
    var g = runGuarded(msg);
    showColumn("g", g, pyEscape(g.reply), msg);
  }

  PRESETS.forEach(function (p) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = p.label;
    b.addEventListener("click", function () { input.value = p.v; update(); });
    presetsEl.appendChild(b);
  });

  input.addEventListener("input", update);
  input.value = PRESETS[1].v;
  update();
})();
