import { useState } from "react";
import { api, Subscription } from "./api";

export default function SubscriptionForm({ initial, onClose, onSaved, onDeleted }: {
  initial?: Subscription;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}) {
  const [f, setF] = useState(initial ? {
    merchant_name: initial.merchant_name,
    amount: String(initial.amount),
    currency: initial.currency,
    billing_cycle: initial.billing_cycle,
    status: initial.status,
    trial_end_date: initial.trial_end_date || "",
    next_renewal_date: initial.next_renewal_date || "",
    notes: initial.notes || "",
  } : {
    merchant_name: "", amount: "", currency: "USD", billing_cycle: "monthly",
    status: "trial", trial_end_date: "", next_renewal_date: "", notes: "",
  });
  const [err, setErr] = useState("");

  function set(k: string, v: string) { setF({ ...f, [k]: v }); }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const payload = {
      ...f,
      amount: parseFloat(f.amount),
      trial_end_date: f.trial_end_date || null,
      next_renewal_date: f.next_renewal_date || null,
      notes: f.notes || null,
    };
    try {
      if (initial) await api.updateSub(initial.id, payload);
      else await api.createSub(payload);
      onSaved();
    } catch (e: any) { setErr(e.message); }
  }

  async function del() {
    if (!initial) return;
    if (!confirm(`Delete ${initial.merchant_name}?`)) return;
    try { await api.deleteSub(initial.id); onDeleted(); }
    catch (e: any) { setErr(e.message); }
  }

  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog" aria-modal="true">
        <div className="grab" />
        <h2>{initial ? "Edit subscription" : "New subscription"}</h2>
        <form className="form" onSubmit={submit}>
          <div className="field wide">
            <label>merchant</label>
            <input required value={f.merchant_name} onChange={(e) => set("merchant_name", e.target.value)} />
          </div>
          <div className="field num">
            <label>amount</label>
            <input type="number" step="0.01" required value={f.amount} onChange={(e) => set("amount", e.target.value)} />
          </div>
          <div className="field">
            <label>currency</label>
            <input value={f.currency} onChange={(e) => set("currency", e.target.value)} />
          </div>
          <div className="field">
            <label>cycle</label>
            <select value={f.billing_cycle} onChange={(e) => set("billing_cycle", e.target.value)}>
              <option value="weekly">weekly</option><option value="monthly">monthly</option><option value="yearly">yearly</option>
            </select>
          </div>
          <div className="field">
            <label>status</label>
            <select value={f.status} onChange={(e) => set("status", e.target.value)}>
              <option value="trial">trial</option><option value="paid">paid</option><option value="cancelled">cancelled</option>
            </select>
          </div>
          <div className="field">
            <label>trial end</label>
            <input type="date" value={f.trial_end_date} onChange={(e) => set("trial_end_date", e.target.value)} />
          </div>
          <div className="field">
            <label>renewal</label>
            <input type="date" value={f.next_renewal_date} onChange={(e) => set("next_renewal_date", e.target.value)} />
          </div>
          <div className="field wide">
            <label>notes</label>
            <input value={f.notes} onChange={(e) => set("notes", e.target.value)} />
          </div>
          {err && <div className="err">{err}</div>}
          <button className="btn accent wide" type="submit">save</button>
        </form>
        {initial && (
          <button className="btn danger wide" onClick={del}>delete subscription</button>
        )}
        <button className="btn wide" onClick={onClose} style={{ marginTop: 10, background: "transparent" }}>cancel</button>
      </div>
    </>
  );
}
