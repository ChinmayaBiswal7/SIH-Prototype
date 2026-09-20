import { useEffect, useState } from "react";
import "./LoadingScreen.css";

const STEPS = [
  "Connecting to sensors...",
  "Loading intersection data...",
  "Calibrating AI models...",
  "Rendering dashboard...",
  "System ready.",
];

export default function LoadingScreen({ onComplete }) {
  const [pct, setPct] = useState(0);
  const [msgIdx, setMsgIdx] = useState(0);

  useEffect(() => {
    let p = 0;
    const iv = setInterval(() => {
      p += 10;
      setPct(Math.min(100, p));
      setMsgIdx(Math.min(STEPS.length - 1, Math.floor(p / 25)));
      if (p >= 100) {
        clearInterval(iv);
        setTimeout(() => {
          onComplete?.();
        }, 150);
      }
    }, 40);
    return () => clearInterval(iv);
  }, []);

  return (
    <div className="ls">
      <div className="ls-box">
        <div className="ls-logo-container">
          <img src="/velociti_logo.png" alt="VeloCiTI" className="ls-logo-img" />
        </div>
        <div className="ls-title">Velo<span>CiTI</span></div>
        <div className="ls-sub">Vehicle Location &amp; City Traffic Intelligence</div>
        <div className="ls-bar-wrap"><div className="ls-bar" style={{ width: `${pct}%` }} /></div>
        <div className="ls-msg">{STEPS[msgIdx]}</div>
      </div>
    </div>
  );
}
