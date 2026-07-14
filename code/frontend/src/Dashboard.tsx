import { useEffect, useState } from "react";
import { api, Subscription } from "./api";
import SubscriptionForm from "./SubscriptionForm";

function monthlyRunRate(subs: Subscription[]): number {
  return subs
    .filter((s) => s.status !== "cancelled")
    .reduce((sum, s) => {
      const m = s.billing_cycle === "weekly" ? 52 / 12 : s.billing_cycle === "yearly" ? 1 / 12 : 1;
      return sum + (parseFloat(String(s.amount)) || 0) * m;
    }, 0);
}

export default function Dashboard() {
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [err, setErr] = useState("");
  const [editing, setEditing] = useState<Subscription | null>(null);
  const [adding, setAdding] = useState(false);

  async function load() {
    try { setSubs(await api.listSubs()); }
    catch (e: any) { setErr(e.message); }
  }
  useEffect(() => { load(); }, []);

  const rate = monthlyRunRate(subs).toFixed(2);
  const activeCount = subs.filter((s) => s.status !== "cancelled").length;
  const trialCount = subs.filter((s) => s.status === "trial").length;

  return (
    <>
      <div className="hero">
        <div className="lbl">monthly run-rate</div>
        <div className="big">${rate}</div>
        <div className="row">
          <div className="pill"><b>{activeCount}</b><span>active</span></div>
          <div className="pill"><b>{trialCount}</b><span>trials</span></div>
        </div>
      </div>

      {err && <div className="banner">{err}</div>}

      {subs.length === 0 ? (
        <div className="empty">
          <div className="big">No subscriptions yet</div>
          <div>Tap + to add your first one.</div>
        </div>
      ) : (
        <div className="cards">
          {subs.map((s, i) => (
            <div className="scard" key={s.id} style={{ animationDelay: `${i * 45}ms` }} onClick={() => setEditing(s)}>
              <span className="avatar">{(s.merchant_name[0] || "?").toUpperCase()}</span>
              <div className="body">
                <div className="name">{s.merchant_name} <span className={`chip ${s.status}`}>{s.status}</span></div>
                <div className="meta">{s.billing_cycle} · renews {s.next_renewal_date || "—"}</div>
              </div>
              <div className="amt"><b>{s.currency} {s.amount}</b><span>{s.billing_cycle}</span></div>
            </div>
          ))}
        </div>
      )}

      <button className="fab" aria-label="Add subscription" onClick={() => setAdding(true)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round"><path d="M12 5v14M5 12h14" /></svg>
      </button>

      {(adding || editing) && (
        <SubscriptionForm
          initial={editing || undefined}
          onClose={() => { setAdding(false); setEditing(null); }}
          onSaved={() => { setAdding(false); setEditing(null); load(); }}
          onDeleted={() => { setEditing(null); load(); }}
        />
      )}
    </>
  );
}
