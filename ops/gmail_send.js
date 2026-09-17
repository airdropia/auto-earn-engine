#!/usr/bin/env bun
/**
 * gmail_send.js — send a Gmail compose from the open Gmail tab via CDP.
 * Does the WHOLE job in ONE run (no interactive retry loop): fill To →
 * Subject → Body → Send → verify → screenshot. Reusable for any email.
 *
 * Usage:
 *   bun ops/gmail_send.js <to> <subject> <body-file> [tab#] [shot.png]
 *
 * Why it will not hang the stream: it is one atomic script — the caller
 * invokes it once and gets one final result. No repeated tool round-trips.
 *
 * Gmail is React-controlled; we use native CDP Input.insertText + full
 * keyboard flow (ctrl+A to clear field first) which React handles reliably.
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";

const PORT = process.env.CDP_PORT || "9222";
const BASE = `http://127.0.0.1:${PORT}`;
const [to, subject, bodyFile, tabArg, shotArg] = process.argv.slice(2);
const tabN = Number(tabArg ?? 0);
const shot = shotArg || "gmail-sent.png";
if (!to || !subject || !bodyFile || !existsSync(bodyFile)) {
  console.error("usage: bun ops/gmail_send.js <to> <subject> <body-file> [tab#] [shot.png]");
  process.exit(1);
}
const body = readFileSync(bodyFile, "utf8").trim();

let seq = 0;
function cdp(ws, method, params = {}) {
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

const SET_VALUE_FN = `(el, text) => {
  const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement : HTMLInputElement;
  Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, text);
  el.dispatchEvent(new Event('input', { bubbles: true }));
  el.dispatchEvent(new Event('change', { bubbles: true }));
  return true;
}`;

async function focusAndFill(ws, selector, text) {
  const r = await cdp(ws, "Runtime.evaluate", {
    expression: `(() => { const el = document.querySelector(${JSON.stringify(selector)}); if (!el) return null; el.focus(); const ok = (${SET_VALUE_FN})(el, ${JSON.stringify(text)}); return ok; })()`,
    returnByValue: true,
  });
  if (r.result?.value !== true) throw new Error(`field not set: ${selector}`);
}

async function main() {
  const tabs = await (await fetch(`${BASE}/json/list`)).json();
  const pages = tabs.filter((t) => t.type === "page");
  const t = pages[tabN];
  if (!t) throw new Error(`no tab #${tabN} (have ${pages.length})`);
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.onopen = () => res(null);
    ws.onerror = () => rej(new Error("ws connect failed"));
  });

  // 1) To
  await focusAndFill(ws, 'input[aria-label="To recipients"]', to);
  // 2) Subject
  await focusAndFill(ws, 'input[name="subjectbox"]', subject);
  // 3) Body
  await focusAndFill(ws, 'textarea[aria-label="Message Body"]', body);
  // 4) Send (click the Send button via JS)
  await new Promise((r) => setTimeout(r, 500));
  const sr = await cdp(ws, "Runtime.evaluate", {
    expression: `(() => {
      const btn = document.querySelector('[role="button"][data-tooltip="Send"]') || [...document.querySelectorAll('[role="button"]')].find(b => (b.getAttribute('data-tooltip') || b.textContent || '').trim().toLowerCase() === 'send');
      if (!btn) return false;
      btn.click(); return true;
    })()`,
    returnByValue: true,
  });
  if (sr.result?.value !== true) throw new Error("Send button not found");

  // 5) Verify: wait for compose window to go away (or send error)
  await new Promise((r) => setTimeout(r, 4000));
  let sent = "unknown", err = "";
  const st = await cdp(ws, "Runtime.evaluate", {
    expression: `(() => {
      const cw = document.querySelector('[role="dialog"][aria-label*="message window"], div[data-id="composewindowbody"], .aA1\\[role=dialog\\]');
      const hasToast = !!document.querySelector('.bAq, [role="alert"]');
      return JSON.stringify({ composeGone: !cw && !document.querySelector('.aA1'), alert: hasToast, body: (document.body.innerText || '').slice(0, 300) });
    })()`,
    returnByValue: true,
  });
  try {
    const d = JSON.parse(st.result.value);
    sent = d.composeGone ? "compose-closed (likely sent)" : "compose-still-open";
    err = d.body.slice(0, 200);
  } catch { /* keep unknown */ }

  // 6) Screenshot for the caller to SEE the page
  const shotRes = await cdp(ws, "Page.captureScreenshot", { format: "png" });
  writeFileSync(shot, Buffer.from(shotRes.data, "base64"));
  try { ws.close(); } catch {}

  console.log(`to=${to}`);
  console.log(`subject=${subject.slice(0, 60)}`);
  console.log(`verify=${sent}`);
  console.log(err ? `page=${err}` : "");
  console.log(`screenshot=${shot} (${existsSync(shot) ? "saved" : "FAILED"})`);
}
main().catch((e) => { console.error("error:", e.message); process.exit(1); });