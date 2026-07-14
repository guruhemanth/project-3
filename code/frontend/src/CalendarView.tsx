import { useEffect, useState } from "react";
import { api, CalendarItem } from "./api";

export default function CalendarView() {
  const [items, setItems] = useState<CalendarItem[]>([]);
  useEffect(() => { api.calendar().then(setItems); }, []);

  return (
    <>
      <h2 className="screen-title">Upcoming</h2>
      <p className="sub">next 90 days · trial ends &amp; renewals</p>
      <ul className="tl">
        {items.map((i, idx) => (
          <li key={idx} style={{ animationDelay: `${idx * 60}ms` }}>
            <div className="when">{i.date}</div>
            <div className="what">{i.merchant_name}</div>
            <div className="kind">{i.kind === "trial_end" ? "trial ends" : "renews"}</div>
          </li>
        ))}
        {items.length === 0 && <li style={{ border: "none" }}><div className="what">nothing scheduled.</div></li>}
      </ul>
    </>
  );
}
