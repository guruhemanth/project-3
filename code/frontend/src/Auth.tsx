import { useState } from "react";
import { api } from "./api";

export default function Auth({ onAuth }: { onAuth: (token: string, email: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      const data = mode === "register"
        ? await api.register(email, password)
        : await api.login(email, password);
      onAuth(data.access_token, email);
    } catch (e: any) { setErr(e.message); }
  }

  return (
    <div className="auth">
      <form className="authcard" onSubmit={submit}>
        <h1>SUB<span className="dot">TRACK</span></h1>
        <div className="sub">{mode === "register" ? "open an account" : "welcome back"}</div>
        <div className="form">
          <div className="field wide">
            <label>email</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field wide">
            <label>password · min 8</label>
            <input type="password" minLength={8} required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          {err && <div className="err">{err}</div>}
          <button className="btn accent wide" type="submit">
            {mode === "register" ? "create account" : "sign in"}
          </button>
        </div>
        <p className="sub" style={{ marginTop: 16, textAlign: "center" }}>
          {mode === "register" ? "already in?" : "new here?"}{" "}
          <button type="button" className="linkbtn"
            onClick={() => setMode(mode === "register" ? "login" : "register")}>
            {mode === "register" ? "sign in" : "create one"}
          </button>
        </p>
      </form>
    </div>
  );
}
