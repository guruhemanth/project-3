import { useEffect, useState } from "react";
import { api, Prefs } from "./api";

export default function Settings({ onLogout }: { onLogout: () => void }) {
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [msg, setMsg] = useState("");
  const [gmail, setGmail] = useState<{ connected: boolean; gmail_enabled: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setPrefs(await api.getPrefs());
    try { setGmail(await api.gmailStatus()); } catch { /* gmail route may be disabled */ }
  }
  useEffect(() => { load(); }, []);

  async function toggle(field: "email_alerts" | "sms_alerts", value: boolean) {
    setMsg("");
    try { setPrefs(await api.updatePrefs({ [field]: value })); }
    catch (e: any) { setMsg(e.message); }
  }
  async function requestOtp() {
    setMsg("");
    try { await api.requestOtp(phone); setMsg("Verification code sent (check console if no Twilio)."); }
    catch (e: any) { setMsg(e.message); }
  }
  async function verifyOtp() {
    setMsg("");
    try { await api.verifyOtp(otp); setMsg("Phone verified!"); await load(); }
    catch (e: any) { setMsg(e.message); }
  }
  async function connectGmail() {
    setBusy(true); setMsg("");
    try {
      const { url } = await api.gmailConnect();
      window.location.href = url; // hands off to Google consent, which redirects back
    } catch (e: any) { setMsg(e.message); setBusy(false); }
  }
  async function ingestGmail() {
    setBusy(true); setMsg("");
    try { const r = await api.gmailIngest(); setMsg(`Imported ${r.created} subscription(s) from Gmail.`); }
    catch (e: any) { setMsg(e.message); }
    finally { setBusy(false); }
  }
  async function sendTestAlert() {
    setBusy(true); setMsg("");
    try { await api.testAlert(); setMsg("Test alert queued — check your inbox."); }
    catch (e: any) { setMsg(e.message); }
    finally { setBusy(false); }
  }

  if (!prefs) return <p style={{ color: "var(--muted-fg)" }}>loading…</p>;
  const bothOff = !prefs.email_alerts && !prefs.sms_alerts;

  return (
    <>
      <h2 className="screen-title">Alerts</h2>

      {bothOff && (
        <div className="banner" role="alert">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <span>All channels off — you'll get no renewal or trial reminders.</span>
        </div>
      )}

      <div className="setrow">
        <div className="t"><b>Email alerts</b><small>required at signup · default ON</small></div>
        <div className={`toggle ${prefs.email_alerts ? "on" : ""}`}
          role="switch" aria-checked={prefs.email_alerts}
          onClick={() => toggle("email_alerts", !prefs.email_alerts)} />
      </div>

      <div className="setrow">
        <div className="t"><b>SMS alerts</b><small>off by default · needs verified phone</small></div>
        <div className={`toggle ${prefs.sms_alerts ? "on" : ""}`}
          role="switch" aria-checked={prefs.sms_alerts}
          onClick={() => {
            if (!prefs.phone_verified) { setMsg("Verify your phone number first to enable SMS alerts."); return; }
            toggle("sms_alerts", !prefs.sms_alerts);
          }} />
      </div>

      <div className="setrow" style={{ display: "block" }}>
        <div className="t" style={{ marginBottom: 10 }}>
          <b>phone</b> <small>{prefs.phone_number || "not set"}{prefs.phone_verified ? " · verified" : ""}</small>
        </div>
        {!prefs.phone_verified && (
          <div className="form">
            <div className="field"><label>number</label><input placeholder="+15551234567" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
            <button className="btn" onClick={requestOtp}>send code</button>
            <div className="field"><label>otp</label><input placeholder="123456" value={otp} onChange={(e) => setOtp(e.target.value)} /></div>
            <button className="btn accent" onClick={verifyOtp}>verify</button>
          </div>
        )}
      </div>

      {msg && <p style={{ color: "var(--muted-fg)", fontFamily: "var(--font-display)", fontSize: 12, marginTop: 14 }}>{msg}</p>}

      {/* Gmail auto-import (Phase 2) */}
      <h2 className="screen-title" style={{ fontSize: 20, marginTop: 22 }}>Auto-import</h2>
      {gmail === null ? (
        <p style={{ color: "var(--muted-fg)", fontSize: 13 }}>loading Gmail status…</p>
      ) : !gmail.gmail_enabled ? (
        <p style={{ color: "var(--muted-fg)", fontSize: 13 }}>
          Auto-import is off. Set <code>feature_flags.gmail_integration: true</code> and an OpenRouter key to enable it.
        </p>
      ) : (
        <div className="setrow" style={{ display: "block" }}>
          <div className="t" style={{ marginBottom: 10 }}>
            <b>Gmail import</b>{" "}
            <small>{gmail.connected ? "connected" : "not connected"}</small>
          </div>
          {gmail.connected ? (
            <button className="btn accent wide" onClick={ingestGmail} disabled={busy}>
              {busy ? "importing…" : "import subscriptions from Gmail"}
            </button>
          ) : (
            <button className="btn accent wide" onClick={connectGmail} disabled={busy}>
              {busy ? "connecting…" : "connect Gmail"}
            </button>
          )}
        </div>
      )}

      <button className="btn wide" onClick={sendTestAlert} disabled={busy} style={{ marginTop: 12 }}>
        {busy ? "sending…" : "send test alert"}
      </button>

      <button className="btn wide" onClick={onLogout} style={{ marginTop: 18, background: "transparent" }}>log out</button>
    </>
  );
}
