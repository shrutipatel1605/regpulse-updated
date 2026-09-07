// Main app — routing, theme, tweaks, command palette

const { useState: uState, useEffect: uEffect } = React;

function App() {
  const [route, setRoute] = uState(() => location.hash.slice(1) || localStorage.getItem("rp:route") || "dashboard");
  const [theme, setTheme] = uState(() => localStorage.getItem("rp:theme") || "light");
  const [tweaksOn, setTweaksOn] = uState(false);
  const [cmdOpen, setCmdOpen] = uState(false);

  uEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("rp:theme", theme);
  }, [theme]);

  uEffect(() => {
    localStorage.setItem("rp:route", route);
    location.hash = route;
  }, [route]);

  uEffect(() => {
    const h = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setCmdOpen(o => !o); }
      if (e.key === "Escape") setCmdOpen(false);
    };
    const c = () => setCmdOpen(o => !o);
    window.addEventListener("keydown", h);
    window.addEventListener("rp:cmd", c);
    return () => { window.removeEventListener("keydown", h); window.removeEventListener("rp:cmd", c); };
  }, []);

  // Tweaks protocol
  uEffect(() => {
    const handler = (e) => {
      const msg = e.data;
      if (!msg || typeof msg !== "object") return;
      if (msg.type === "__activate_edit_mode") setTweaksOn(true);
      if (msg.type === "__deactivate_edit_mode") setTweaksOn(false);
    };
    window.addEventListener("message", handler);
    try { window.parent.postMessage({ type: "__edit_mode_available" }, "*"); } catch(_) {}
    return () => window.removeEventListener("message", handler);
  }, []);

  const Page = {
    dashboard: Dashboard, ask: Ask, updates: Updates, library: Library,
    actions: ActionItems, history: History, saved: Saved, learnings: Learnings,
    debate: Debate, upgrade: Upgrade, account: Account, admin: Admin,
  }[route] || Dashboard;

  return (
    <ToastProvider>
      <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
        <TopBar onToggleTheme={() => setTheme(t => t === "dark" ? "light" : "dark")} theme={theme} onRoute={setRoute} />
        <Ticker />
        <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
          <Sidebar current={route} onRoute={setRoute} />
          <main style={{ flex: 1, overflow: "hidden", background: "var(--bg)" }}>
            <div key={route} style={{ height: "100%", overflow: "auto", animation: "fadeIn .2s ease" }}>
              <Page onRoute={setRoute} />
            </div>
          </main>
        </div>
      </div>

      {cmdOpen ? <CommandPalette onClose={() => setCmdOpen(false)} onRoute={(r) => { setRoute(r); setCmdOpen(false); }} /> : null}

      {tweaksOn ? <TweaksPanel theme={theme} setTheme={setTheme} /> : null}
    </ToastProvider>
  );
}

function CommandPalette({ onClose, onRoute }) {
  const [q, setQ] = uState("");
  const items = [
    ...NAV.map(n => ({ ...n, group: "Navigate" })),
    { id: "ask", label: "Ask: Tier-1 impact of SBR revision", icon: Icon.Ask, group: "Recent asks" },
    { id: "ask", label: "Ask: PSL climate-adaptive sub-target", icon: Icon.Ask, group: "Recent asks" },
    { id: "library", label: "DOR.CAP.REC.22 · SBR Revision", icon: Icon.Book, group: "Circulars" },
    { id: "library", label: "DOR.AML.REC.18 · KYC Amendment", icon: Icon.Book, group: "Circulars" },
  ];
  const filtered = items.filter(i => q === "" || i.label.toLowerCase().includes(q.toLowerCase()));
  const groups = filtered.reduce((acc, it) => { (acc[it.group] = acc[it.group] || []).push(it); return acc; }, {});
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 200, background: "rgba(0,0,0,.35)", display: "flex", justifyContent: "center", paddingTop: 120 }}>
      <div onClick={e => e.stopPropagation()} style={{ width: 560, height: "fit-content", background: "var(--panel)", border: "1px solid var(--line-2)", borderRadius: 4, boxShadow: "var(--shadow-lg)", overflow: "hidden" }}>
        <div style={{ padding: 12, borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
          <Icon.Search style={{ color: "var(--ink-3)" }} />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Ask, search, or jump…"
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 14 }} />
          <Kbd>ESC</Kbd>
        </div>
        <div style={{ maxHeight: 400, overflowY: "auto", padding: "6px 0" }}>
          {Object.entries(groups).map(([g, items]) => (
            <div key={g}>
              <div className="mono up" style={{ fontSize: 9.5, color: "var(--ink-4)", padding: "8px 14px 4px" }}>{g}</div>
              {items.map((it, i) => {
                const Ic = it.icon;
                return (
                  <div key={i} onClick={() => onRoute(it.id)} style={{
                    padding: "8px 14px", fontSize: 13, cursor: "pointer",
                    display: "flex", alignItems: "center", gap: 10,
                  }} onMouseOver={e => e.currentTarget.style.background = "var(--panel-2)"}
                     onMouseOut={e => e.currentTarget.style.background = "transparent"}>
                    <Ic style={{ color: "var(--ink-4)" }} />
                    {it.label}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TweaksPanel({ theme, setTheme }) {
  const [density, setDensity] = uState("compact");
  const [font, setFont] = uState("editorial");
  const [accent, setAccent] = uState("amber");
  uEffect(() => {
    const r = document.documentElement;
    const m = { amber: "#c25a11", emerald: "#12734f", crimson: "#a22020", cobalt: "#1c4ebc" };
    if (m[accent]) r.style.setProperty("--signal", m[accent]);
  }, [accent]);
  return (
    <div style={{
      position: "fixed", bottom: 20, right: 20, width: 260,
      background: "var(--panel)", border: "1px solid var(--line-2)",
      boxShadow: "var(--shadow-lg)", zIndex: 150, borderRadius: 4,
    }}>
      <div style={{ padding: "10px 14px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 8 }}>
        <Icon.Settings style={{ color: "var(--signal)" }} />
        <span style={{ fontWeight: 600, fontSize: 12.5 }}>Tweaks</span>
      </div>
      <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 14 }}>
        <TweakRow label="Theme" options={[["light","Light"],["dark","Dark"]]} value={theme} onChange={setTheme} />
        <TweakRow label="Accent" options={[["amber","Amber"],["emerald","Emerald"],["crimson","Crimson"],["cobalt","Cobalt"]]} value={accent} onChange={setAccent} />
        <TweakRow label="Density" options={[["compact","Compact"],["normal","Normal"]]} value={density} onChange={setDensity} />
        <TweakRow label="Answer style" options={[["editorial","Editorial"],["memo","Memo"]]} value={font} onChange={setFont} />
      </div>
    </div>
  );
}

function TweakRow({ label, options, value, onChange }) {
  return (
    <div>
      <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 6 }}>{label}</div>
      <div style={{ display: "flex", gap: 4 }}>
        {options.map(([k, l]) => (
          <button key={k} onClick={() => onChange(k)} style={{
            flex: 1, fontSize: 11.5, padding: "5px 0",
            border: `1px solid ${value === k ? "var(--signal)" : "var(--line)"}`,
            background: value === k ? "var(--signal-bg)" : "var(--bg)",
            color: value === k ? "var(--signal-ink)" : "var(--ink-2)",
            borderRadius: 2, cursor: "pointer",
          }}>{l}</button>
        ))}
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
