#!/usr/bin/env bun
// pinterest_demo.js - One-command demo for Pinterest Standard-access review.
//
// WHAT IT DOES (all on screen, easy to record):
//   1. Builds the OAuth authorize URL and OPENS it in your browser
//   2. Waits for you to paste the callback URL (the 404 page's address)
//   3. Exchanges the code -> access token (shows OAuth flow works)
//   4. GET /v5/user_account           (shows auth works)
//   5. POST /v5/boards                 (shows live write/integration works)
//   6. Prints "DEMO PASS"
//
// RUN:  bun ops/pinterest_demo.js
// Secrets read from ~/.pi/secrets/pinterest.env (app secret + PKCE).

import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

const ENV_PATH = join(homedir(), ".pi", "secrets", "pinterest.env");
const APP_ID = "1604703";
const REDIRECT_URI = "https://airdropia.github.io/auto-earn-engine/oauth-callback";
const SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read";

function loadEnv() {
  const env = {};
  if (!existsSync(ENV_PATH)) return env;
  for (const line of readFileSync(ENV_PATH, "utf8").split("\n")) {
    const t = line.trim();
    if (!t || t.startsWith("#") || !t.includes("=")) continue;
    const i = t.indexOf("=");
    env[t.slice(0, i).trim()] = t.slice(i + 1).trim();
  }
  return env;
}

function saveEnv(env) {
  const lines = Object.entries(env).filter(([, v]) => v).map(([k, v]) => `${k}=${v}`);
  writeFileSync(ENV_PATH, lines.join("\n") + "\n");
}

function b64url(buf) {
  return Buffer.from(buf).toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function line() {
  console.log("-".repeat(64));
}

const env = loadEnv();
if (!env.PINTEREST_APP_SECRET) {
  console.error("ERROR: PINTEREST_APP_SECRET missing in " + ENV_PATH);
  process.exit(1);
}

// Fresh PKCE for this run
const verifier = Buffer.from(crypto.getRandomValues(new Uint8Array(43))).toString("base64url").slice(0, 64);
const challenge = b64url(createHash("sha256").update(verifier).digest());
env.PINTEREST_PKCE_VERIFIER = verifier;
env.PINTEREST_PKCE_CHALLENGE = challenge;
saveEnv(env);

const authUrl =
  "https://www.pinterest.com/oauth/?" +
  new URLSearchParams({
    client_id: APP_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    state: "vfd-demo",
    scope: SCOPES,
    code_challenge: challenge,
    code_challenge_method: "S256",
  }).toString();

line();
console.log("VECTORFORGE DAILY - Pinterest API demo (for Standard-access review)");
line();
console.log("STEP 1: signing in and approving the app in your browser...");
console.log("        (if the browser does not open, copy this URL manually)");
console.log("");
console.log(authUrl);
console.log("");
try {
  Bun.spawnSync(["cmd", "/c", "start", "", authUrl]);
} catch {
  // ignore - user can copy the URL above
}
console.log("STEP 2: after you click Approve, the browser lands on a 404 page.");
console.log("        Copy the FULL address-bar URL (it contains code=...) and paste below.");
console.log("");

const pasted = (prompt("Paste callback URL here:") || "").trim();
let code = pasted;
if (code.includes("?")) {
  const q = new URLSearchParams(code.split("?")[1]);
  code = q.get("code") || "";
}
if (!code) {
  console.error("ERROR: no code found in what you pasted.");
  process.exit(1);
}

line();
console.log("[1/3] Exchanging authorization code for an access token...");
const basic = Buffer.from(`${APP_ID}:${env.PINTEREST_APP_SECRET}`).toString("base64");
const tokenRes = await fetch("https://api.pinterest.com/v5/oauth/token", {
  method: "POST",
  headers: {
    Authorization: `Basic ${basic}`,
    "Content-Type": "application/x-www-form-urlencoded",
  },
  body: new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: APP_ID,
    code_verifier: verifier,
  }),
});
const tokenJson = await tokenRes.json();
const token = tokenJson.access_token || "";
if (!token) {
  console.error("  FAIL: " + JSON.stringify(tokenJson).slice(0, 220));
  process.exit(1);
}
env.PINTEREST_ACCESS_TOKEN = token;
env.PINTEREST_TOKEN_SCOPES = tokenJson.scope || "";
saveEnv(env);
console.log(`  OK  token received (${token.length} chars)`);
console.log(`  OK  scopes: ${tokenJson.scope || "(see response)"}`);

console.log("[2/3] Live API call: GET /v5/user_account");
const accRes = await fetch("https://api.pinterest.com/v5/user_account", {
  headers: { Authorization: `Bearer ${token}` },
});
const acc = await accRes.json();
if (accRes.status !== 200) {
  console.error(`  FAIL HTTP ${accRes.status}: ${JSON.stringify(acc).slice(0, 200)}`);
  process.exit(1);
}
console.log(`  OK  HTTP ${accRes.status} - account: ${acc.business_name || acc.username}`);

console.log("[3/3] Live API call: POST /v5/boards (create demo board)");
const boardRes = await fetch("https://api.pinterest.com/v5/boards", {
  method: "POST",
  headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
  body: JSON.stringify({
    name: "VectorForge API Demo",
    description: "Live integration demo for Standard access review",
    privacy: "PUBLIC",
  }),
});
const board = await boardRes.json();
if (boardRes.status !== 200 && boardRes.status !== 201) {
  console.error(`  FAIL HTTP ${boardRes.status}: ${JSON.stringify(board).slice(0, 200)}`);
  process.exit(1);
}
console.log(`  OK  HTTP ${boardRes.status} - board created: ${board.name} (id ${board.id})`);

line();
console.log("DEMO PASS - OAuth flow + live Pinterest API integration verified.");
line();