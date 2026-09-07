// App shell — topbar, sidebar, ticker, command palette hint

const NAV = [
  { id: "dashboard", label: "Dashboard", icon: Icon.Grid },
  { id: "ask",       label: "Ask",       icon: Icon.Ask,  kbd: "A" },
  { id: "updates",   label: "Updates",   icon: Icon.Pulse, badge: 7 },
  { id: "library",   label: "Library",   icon: Icon.Book },
  { id: "actions",   label: "Action Items", icon: Icon.Flag, badge: 5 },
  { id: "history",   label: "History",   icon: Icon.Search },
  { id: "saved",     label: "Saved",     icon: Icon.Bookmark },
  { id: "learnings", label: "Learnings", icon: Icon.Spark, signal: true },
  { id: "debate",    label: "Debate",    icon: Icon.Users, badge: 2 },
];

const NAV_BOTTOM = [
  { id: "upgrade",  label: "Upgrade",  icon: Icon.Plus },
  { id: "account",  label: "Account",  icon: Icon.Settings },
  { id: "admin",    label: "Admin",    icon: Icon.Settings, tag: "ADMIN" },
];

// --- Ticker ---
function Ticker() {
  const items = RP_DATA.market.ticker;
  // Duplicate for seamless loop
  const loop = [...items, ...items];
  return (
    <div style={{
      borderBottom: "1px solid var(--line)",
      background: "var(--panel)",
      overflow: "hidden",
      height: 28,
      position: "relative",
      flexShrink: 0,
    }}>
      <div className="ticker-track" style={{ padding: "6px 0" }}>
        {loop.map((t, i) => (
          <span key={i} style={{ display: "inline-flex", alignItems: "center", gap: 8, fontSize: 11.5 }}>
            <span className="mono" style={{
              fontSize: 10, padding: "1px 5px", borderRadius: 2,
              background: t.impact === "high" ? "var(--signal-bg)" :
                          t.impact === "med"  ? "var(--warn-bg)" : "var(--bg-2)",
              color:      t.impact === "high" ? "var(--signal-ink)" :
                          t.impact === "med"  ? "var(--warn)" : "var(--ink-3)",
              letterSpacing: ".08em",
            }}>{t.tag}</span>
            <span style={{ color: "var(--ink-2)" }}>{t.text}</span>
            <span style={{ color: "var(--ink-5)" }}>•</span>
          </span>
        ))}
      </div>
    </div>
  );
}

// --- Topbar ---
function TopBar({ onToggleTheme, theme, onRoute }) {
  const u = RP_DATA.user;
  const m = RP_DATA.market;
  return (
    <div style={{
      height: 52, flexShrink: 0,
      background: "var(--panel)",
      borderBottom: "1px solid var(--line)",
      display: "flex", alignItems: "center",
      padding: "0 16px", gap: 16,
    }}>
      {/* Logo */}
      <div onClick={() => onRoute("dashboard")} style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{
          width: 26, height: 26,
          background: "var(--ink)", color: "var(--bg)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 13,
          borderRadius: 3, position: "relative",
        }}>
          <span>R</span>
          <span className="live-dot" style={{
            position: "absolute", top: -2, right: -2, width: 6, height: 6, background: "var(--signal)"
          }} />
        </div>
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1 }}>
          <span style={{ fontWeight: 600, fontSize: 14, letterSpacing: "-0.01em" }}>RegPulse</span>
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".1em", marginTop: 2 }}>TERMINAL · v2.0</span>
        </div>
      </div>

      <div style={{ width: 1, height: 24, background: "var(--line)" }} />

      {/* Live market bar */}
      <div style={{ display: "flex", gap: 18, alignItems: "center", fontSize: 11 }}>
        <LiveStat label="REPO" value={m.rbiRate.repo.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="CRR"  value={m.rbiRate.crr.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="SLR"  value={m.rbiRate.slr.toFixed(2) + "%"} trend="flat" />
        <LiveStat label="USD/INR" value={m.usdInr.toFixed(2)} trend="up" delta="+0.14"/>
      </div>

      <div style={{ flex: 1 }} />

      {/* Command bar */}
      <div
        onClick={() => { window.dispatchEvent(new CustomEvent("rp:cmd")); }}
        style={{
          display: "flex", alignItems: "center", gap: 8,
          height: 30, padding: "0 10px", minWidth: 300,
          border: "1px solid var(--line)",
          borderRadius: 3,
          background: "var(--bg-1)",
          color: "var(--ink-3)",
          cursor: "pointer", fontSize: 12,
        }}>
        <Icon.Search style={{ opacity: 0.6 }} />
        <span>Ask anything, or jump to a circular…</span>
        <span style={{ flex: 1 }} />
        <Kbd>⌘K</Kbd>
      </div>

      {/* Credits */}
      <div
        onClick={() => onRoute("upgrade")}
        style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 12 }}>
        <span className="mono up" style={{ color: "var(--ink-4)", fontSize: 10 }}>CREDITS</span>
        <span className="mono tnum" style={{ fontWeight: 600 }}>{u.credits}</span>
        <div style={{ width: 48 }}>
          <div className="bar amber"><span style={{ width: `${Math.min(100, u.credits / 3)}%` }}/></div>
        </div>
      </div>

      {/* Theme */}
      <Btn variant="ghost" icon onClick={onToggleTheme} title="Toggle theme">
        {theme === "dark" ? <Icon.Sun /> : <Icon.Moon />}
      </Btn>

      {/* Avatar */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Avatar initials={u.initials} size={28} tone="signal" />
        <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.2 }}>
          <span style={{ fontSize: 12, fontWeight: 500 }}>{u.name}</span>
          <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)" }}>{u.org.toUpperCase()}</span>
        </div>
      </div>
    </div>
  );
}

function LiveStat({ label, value, trend, delta }) {
  const color = trend === "up" ? "var(--good)" : trend === "down" ? "var(--bad)" : "var(--ink-3)";
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
      <span className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".08em" }}>{label}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span className="mono tnum" style={{ fontWeight: 600, fontSize: 12 }}>{value}</span>
        {delta ? <span className="mono tnum" style={{ fontSize: 10, color }}>{delta}</span> : null}
      </div>
    </div>
  );
}

// --- Sidebar ---
function Sidebar({ current, onRoute }) {
  return (
    <aside style={{
      width: 220, flexShrink: 0,
      background: "var(--panel)",
      borderRight: "1px solid var(--line)",
      display: "flex", flexDirection: "column",
      padding: "12px 0",
      overflowY: "auto",
    }}>
      <SidebarGroup label="Workspace">
        {NAV.map(item => (
          <NavRow key={item.id} item={item} current={current} onRoute={onRoute} />
        ))}
      </SidebarGroup>

      <div style={{ flex: 1 }} />

      <SidebarGroup label="Account">
        {NAV_BOTTOM.map(item => (
          <NavRow key={item.id} item={item} current={current} onRoute={onRoute} />
        ))}
      </SidebarGroup>

      {/* Live pulse mini */}
      <div style={{ padding: "14px 16px 10px", borderTop: "1px solid var(--line)" }}>
        <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".12em", marginBottom: 8 }}>
          <span className="live-dot" style={{ marginRight: 6, verticalAlign: "middle" }} />
          LIVE · INDEX ACTIVE
        </div>
        <div style={{ fontSize: 11, color: "var(--ink-3)", lineHeight: 1.5 }}>
          Crawler indexed <b style={{ color: "var(--ink)" }}>{RP_DATA.pulse.thisWeek}</b> new circulars this week. Last scan: <b style={{ color: "var(--ink)" }}>2m ago</b>.
        </div>
      </div>
    </aside>
  );
}

function SidebarGroup({ label, children }) {
  return (
    <div style={{ padding: "8px 0" }}>
      <div className="mono" style={{
        fontSize: 9.5, color: "var(--ink-4)", letterSpacing: ".12em",
        padding: "4px 16px 8px",
      }}>{label.toUpperCase()}</div>
      {children}
    </div>
  );
}

function NavRow({ item, current, onRoute }) {
  const active = current === item.id;
  const Ic = item.icon;
  return (
    <div
      onClick={() => onRoute(item.id)}
      style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "7px 16px", cursor: "pointer",
        color: active ? "var(--ink)" : "var(--ink-3)",
        background: active ? "var(--panel-2)" : "transparent",
        borderLeft: `2px solid ${active ? "var(--signal)" : "transparent"}`,
        fontSize: 12.5,
        fontWeight: active ? 600 : 400,
        transition: "background .12s",
      }}>
      <Ic style={{ opacity: active ? 1 : 0.7 }} />
      <span style={{ flex: 1 }}>{item.label}</span>
      {item.kbd ? <Kbd>{item.kbd}</Kbd> : null}
      {item.badge ? (
        <span className="mono" style={{
          fontSize: 10, fontWeight: 600,
          background: item.signal ? "var(--signal)" : "var(--bg-2)",
          color: item.signal ? "#fff" : "var(--ink-3)",
          padding: "1px 5px", borderRadius: 2, minWidth: 18, textAlign: "center",
        }}>{item.badge}</span>
      ) : null}
      {item.signal && !item.badge ? (
        <span className="live-dot" style={{ width: 6, height: 6 }} />
      ) : null}
      {item.tag ? (
        <span className="mono" style={{
          fontSize: 9, padding: "1px 4px", background: "var(--bg-2)",
          color: "var(--ink-4)", letterSpacing: ".1em", borderRadius: 2,
        }}>{item.tag}</span>
      ) : null}
    </div>
  );
}

Object.assign(window, { TopBar, Sidebar, Ticker, NAV, NAV_BOTTOM });
