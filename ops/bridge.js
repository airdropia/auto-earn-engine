#!/usr/bin/env bun
/**
 * ops/bridge.js — zero-dep CDP bridge: pi controls a Brave tab the user
 * signed into manually.
 *
 * How it works: Brave/Chrome expose the DevTools protocol on a local port.
 * User opens Brave via `launch` (dedicated work profile), signs in to the
 * target site by hand, then the agent drives that tab over CDP.
 *
 * Usage:
 *   bun ops/bridge.js launch                     # start Brave with CDP port (work profile)
 *   bun ops/bridge.js tabs                       # list open tabs
 *   bun ops/bridge.js goto <url> [tab#]          # navigate tab
 *   bun ops/bridge.js eval "<js>" [tab#]         # run JS in page, print result
 *   bun ops/bridge.js click "<selector>" [tab#]  # click via JS
 *   bun ops/bridge.js type "<selector>" "<text>" [tab#]  # set input value (+input/change events)
 *   bun ops/bridge.js shot [out.png] [tab#]      # screenshot -> png
 *   bun ops/bridge.js upload "<selector>" "<file>" [tab#]  # native file-input set
 *
 * Env: CDP_PORT (9222), BRAVE_PATH, BRAVE_PROFILE
 *
 * SECURITY: an open CDP port = full control of that browser profile
 * (cookies included). Keep it to the dedicated work profile and close the
 * window when done; never run with the debug port for personal browsing.
 */
import { writeFileSync } from "node:fs";
import { spawn } from "node:child_process";

const PORT = process.env.CDP_PORT || "9222";
const BASE = `http://127.0.0.1:${PORT}`;
const BRAVE =
  process.env.BRAVE_PATH ||
  "C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe";
// Verified 2026-09-17 (Brave 152): REAL default profile works with CDP —
// the dedicated-profile workaround is NOT needed. Using the user's actual
// profile means all their existing logins/cookies are available to the bridge.
const USER_DATA = process.env.BRAVE_USER_DATA ||
  "C:\\Users\\Admin\\AppData\\Local\\BraveSoftware\\Brave-Browser\\User Data";
const PROFILE_DIR = process.env.BRAVE_PROFILE_DIR || "Default";  // from Local State: profile.last_used

const [cmd, ...args] = process.argv.slice(2);

async function targets() {
  const r = await fetch(`${BASE}/json/list`);
  if (!r.ok) throw new Error(`CDP not reachable on :${PORT}`);
  return (await r.json()).filter((t) => t.type === "page");
}

let seq = 0;
function call(ws, method, params = {}) {
  const id = ++seq;
  return new Promise((res, rej) => {
    const on = (ev) => {
      const m = JSON.parse(String(ev.data));
      if (m.id === id) {
        ws.removeEventListener("message", on);
        m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
      }
    };
    ws.addEventListener("message", on);
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function session(n = 0) {
  const ts = await targets();
  const t = ts[Number(n)];
  if (!t) throw new Error(`no tab #${n} (have ${ts.length}). Try: bun ops/bridge.js tabs`);
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = res;
    ws.onerror = () => rej(new Error("ws connect failed (is Brave running with the port?)"));
  });
  return { ws, t };
}

const SET_VALUE = `(sel, text) => {
  const el = document.querySelector(sel);
  if (!el) throw new Error("not found: " + sel);
  const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement : HTMLInputElement;
  Object.getOwnPropertyDescriptor(proto.prototype, "value").set.call(el, text);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}`;

async function main() {
  if (cmd === "launch") {
    spawn(BRAVE, [
      `--remote-debugging-port=${PORT}`,
      `--user-data-dir=${USER_DATA}`,
      `--profile-directory=${PROFILE_DIR}`,
      "--remote-allow-origins=*",
      "--no-first-run",
      "--no-default-browser-check",
      "about:blank",
    ], { detached: true, stdio: "ignore" }).unref();
    console.log(`Brave launched (REAL profile: ${PROFILE_DIR}, CDP: ${PORT}). Your existing logins are live. Sign in where needed, then: bun ops/bridge.js tabs`);
    return;
  }
  if (cmd === "tabs") {
    const ts = await targets();
    ts.forEach((t, i) => console.log(`#${i}  ${t.title}  |  ${t.url}`));
    return;
  }
  if (!cmd) throw new Error("usage: launch|tabs|goto|eval|click|type|shot|upload");

  const [a, b, c] = args;
  const n = cmd === "goto" || cmd === "eval" || cmd === "click" || cmd === "shot" || cmd === "upload" ? args.at(-1) : undefined;
  const tab = /^\d+$/.test(String(n)) ? n : "0";
  const { ws, t } = await session(tab);

  if (cmd === "goto") {
    await call(ws, "Page.navigate", { url: a });
    console.log(`tab#${tab} -> ${a}`);
  } else if (cmd === "eval") {
    const r = await call(ws, "Runtime.evaluate", { expression: a, returnByValue: true, awaitPromise: true });
    console.log(JSON.stringify(r.result?.value ?? r.result, null, 1));
  } else if (cmd === "click") {
    const r = await call(ws, "Runtime.evaluate", { expression: `(() => { const el = document.querySelector(${JSON.stringify(a)}); if (!el) throw new Error("not found: ${a}"); el.click(); return true; })()`, returnByValue: true });
    console.log(r.result?.value ? `clicked ${a} on tab#${tab} (${t.title})` : JSON.stringify(r));
  } else if (cmd === "type") {
    const r = await call(ws, "Runtime.evaluate", {
      expression: `(${SET_VALUE})(${JSON.stringify(a)}, ${JSON.stringify(b)})`,
      returnByValue: true,
    });
    console.log(r.result?.value ? `typed into ${a} on tab#${tab}` : JSON.stringify(r));
  } else if (cmd === "shot") {
    const r = await call(ws, "Page.captureScreenshot", { format: "png" });
    const file = a && !/^\d+$/.test(a) ? a : `shot-tab${tab}.png`;
    writeFileSync(file, Buffer.from(r.data, "base64"));
    console.log(`saved ${file} (${Buffer.from(r.data, "base64").length}B)`);
  } else if (cmd === "upload") {
    const doc = await call(ws, "DOM.getDocument", { depth: -1 });
    const node = await call(ws, "DOM.querySelector", { nodeId: doc.root.nodeId, selector: a });
    if (!node.nodeId) throw new Error(`file input not found: ${a}`);
    await call(ws, "DOM.setFileInputFiles", { files: [b], nodeId: node.nodeId });
    console.log(`set ${b} into ${a}`);
  } else {
    throw new Error(`unknown cmd: ${cmd}`);
  }
  ws.close();
}

main().catch((e) => {
  console.error(`error: ${e.message}`);
  process.exit(1);
});
