// Shared small components used across screens.
// Depends on window.RP_DATA

const { useState, useEffect, useRef, useMemo } = React;

// ---------- Primitives ----------

const cn = (...parts) => parts.filter(Boolean).join(" ");

function Pill({ children, tone = "", className = "", ...rest }) {
  return (
    <span className={cn("pill", tone, className)} {...rest}>{children}</span>
  );
}

function Tick({ children, right }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
      <div className="tick">{children}</div>
      {right ? <div style={{ flex: 1, height: 1, background: "var(--line)" }} /> : null}
      {right}
    </div>
  );
}

function Btn({ children, variant = "", size = "", icon = false, className = "", ...rest }) {
  return (
    <button className={cn("btn", variant, size, icon && "icon", className)} {...rest}>
      {children}
    </button>
  );
}

function Kbd({ children }) { return <kbd>{children}</kbd>; }

// Tiny SVG icons (hand-rolled minimal line icons)
const Icon = {
  Search:  (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>),
  Ask:     (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 4h18v14h-8l-5 4v-4H3z"/></svg>),
  Book:    (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 4h10a4 4 0 0 1 4 4v12H8a4 4 0 0 0-4 4V4z"/><path d="M20 20H8a4 4 0 0 0-4 4"/></svg>),
  Pulse:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 12h3l3-9 4 18 3-9h5"/></svg>),
  Check:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 12l5 5L21 4"/></svg>),
  Flag:    (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 22V4s3-2 7 0 7 0 7 0v12s-3 2-7 0-7 0-7 0"/></svg>),
  Bookmark:(p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 3h14v18l-7-5-7 5z"/></svg>),
  Grid:    (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>),
  Spark:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>),
  Users:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="9" cy="8" r="4"/><path d="M2 22c0-4 3-7 7-7s7 3 7 7"/><circle cx="17" cy="8" r="3"/><path d="M22 21c0-3-2-5-5-5"/></svg>),
  Settings:(p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>),
  Sun:     (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>),
  Moon:    (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>),
  Arrow:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 12h14M13 6l6 6-6 6"/></svg>),
  Up:      (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m6 15 6-6 6 6"/></svg>),
  Down:    (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="m6 9 6 6 6-6"/></svg>),
  Tag:     (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M20 12 12 20l-9-9V3h8z"/><circle cx="7.5" cy="7.5" r="1"/></svg>),
  Plus:    (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 5v14M5 12h14"/></svg>),
  Close:   (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M6 6l12 12M18 6 6 18"/></svg>),
  Thumb:   (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M7 10v11H3V10zM7 10l5-8a2 2 0 0 1 3 2l-1 6h5a2 2 0 0 1 2 2l-2 8a2 2 0 0 1-2 1H7"/></svg>),
  ThumbD:  (p) => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p} style={{ transform: "scaleY(-1)", ...(p.style||{}) }}><path d="M7 10v11H3V10zM7 10l5-8a2 2 0 0 1 3 2l-1 6h5a2 2 0 0 1 2 2l-2 8a2 2 0 0 1-2 1H7"/></svg>),
  Pin:     (p) => (<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 2v8M8 10h8l-1 5H9zM12 15v7"/></svg>),
};

// ---------- Sparkline ----------
function Sparkline({ data, width = 100, height = 28, stroke = "var(--signal)", fill = "rgba(194,90,17,0.12)" }) {
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => [i * step, height - ((v - min) / range) * height]);
  const path = points.map(([x, y], i) => (i === 0 ? `M${x},${y}` : `L${x},${y}`)).join(" ");
  const area = `${path} L${width},${height} L0,${height} Z`;
  return (
    <svg width={width} height={height} style={{ display: "block" }}>
      <path d={area} fill={fill} />
      <path d={path} stroke={stroke} strokeWidth="1.25" fill="none" />
    </svg>
  );
}

// ---------- Avatar ----------
function Avatar({ initials, size = 24, tone = "default" }) {
  const bg = tone === "signal" ? "var(--signal)" : "var(--ink-3)";
  const color = tone === "signal" ? "#fff" : "var(--bg)";
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%",
      background: bg, color, fontFamily: "var(--font-mono)",
      fontSize: size * 0.4, fontWeight: 600,
      display: "inline-flex", alignItems: "center", justifyContent: "center",
      letterSpacing: 0, flexShrink: 0,
    }}>{initials}</div>
  );
}

// ---------- Toast system (imperative) ----------
const ToastContext = React.createContext(null);
function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = (t) => {
    const id = Math.random().toString(36).slice(2);
    const toast = { id, ...t };
    setToasts((prev) => [...prev, toast]);
    setTimeout(() => setToasts((prev) => prev.filter(x => x.id !== id)), 3800);
  };
  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-stack">
        {toasts.map(t => (
          <div key={t.id} className="toast">
            <span className="tmono">{t.tag || "OK"}</span>
            <span>{t.text}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
const useToast = () => React.useContext(ToastContext);

// Export
Object.assign(window, {
  cn, Pill, Tick, Btn, Kbd, Icon, Sparkline, Avatar, ToastProvider, useToast,
});
