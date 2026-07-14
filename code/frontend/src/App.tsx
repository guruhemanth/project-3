import { useEffect, useState } from "react";
import { clearToken, getToken, setOnUnauthorized, setToken } from "./api";
import Dashboard from "./Dashboard";
import CalendarView from "./CalendarView";
import Settings from "./Settings";
import Auth from "./Auth";

type Tab = "ledger" | "calendar" | "alerts";

const ICONS: Record<string, string> = {
  ledger: "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  alerts: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
};
const TABS: { id: Tab; label: string }[] = [
  { id: "ledger", label: "Ledger" },
  { id: "calendar", label: "Calendar" },
  { id: "alerts", label: "Alerts" },
];

function TabIcon({ name }: { name: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name] || ""} />
    </svg>
  );
}

export default function App() {
  const [token, setTok] = useState<string | null>(getToken());
  const [tab, setTab] = useState<Tab>("ledger");
  const [email, setEmail] = useState("");

  useEffect(() => { setOnUnauthorized(() => setTok(null)); }, []);

  if (!token) return <Auth onAuth={(t, e) => { setToken(t); setEmail(e); setTok(t); }} />;

  return (
    <div className="app">
      <header className="topbar">
        <h1 className="wordmark">SUB<span className="dot">TRACK</span></h1>
        <div className="who" aria-hidden="true">{email ? email[0].toUpperCase() : "?"}</div>
      </header>

      <main className="screen tab-in" key={tab}>
        {tab === "ledger" && <Dashboard />}
        {tab === "calendar" && <CalendarView />}
        {tab === "alerts" && <Settings onLogout={() => { clearToken(); setTok(null); }} />}
      </main>

      <nav className="tabbar">
        {TABS.map((t) => (
          <button key={t.id} className={`tab ${tab === t.id ? "on" : ""}`} onClick={() => setTab(t.id)}
            aria-current={tab === t.id ? "page" : undefined}>
            <TabIcon name={t.id} />
            <span>{t.label}</span>
          </button>
        ))}
      </nav>
    </div>
  );
}
