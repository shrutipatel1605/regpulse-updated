// Remaining pages — Updates, Library, Actions, History, Saved, Learnings, Debate, Upgrade, Account, Admin

function Updates({ onRoute }) {
  const [tab, setTab] = useState("circ");
  const circ = RP_DATA.circulars.filter(c => c.status === "active");
  const news = [
    { src: "RBI Press", title: "Governor opens ECL consultation; banks given 60 days", when: "1h ago", relevance: 92 },
    { src: "Business Standard", title: "Axis, HDFC brief RBI on digital lending guardrails", when: "3h ago", relevance: 81 },
    { src: "LiveMint", title: "SBR Upper-Layer NBFCs get 3-quarter glide path for capital build-up", when: "6h ago", relevance: 88, linked: "c1" },
    { src: "ET Banking", title: "Priority sector shortfall filings — 9 banks expected to miss FY26", when: "Yday", relevance: 75 },
    { src: "RBI Press", title: "FEMA — ECB SOFR linkage deadline extended by 90 days", when: "Yday", relevance: 96, linked: "c3" },
  ];
  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 400, letterSpacing: "-0.01em" }}>Updates</h1>
        <span className="live-dot" />
        <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>LAST SCAN · 2m AGO</span>
        <div style={{ flex: 1 }} />
        <Btn size="sm" variant="ghost">RSS feeds</Btn>
        <Btn size="sm">Subscribe to digest</Btn>
      </div>
      <div style={{ display: "flex", gap: 2, borderBottom: "1px solid var(--line)", marginBottom: 14 }}>
        {[["circ","RBI Circulars",circ.length],["news","Market News", news.length],["cons","Consultations", 3]].map(([id,l,n]) => (
          <button key={id} onClick={() => setTab(id)} style={{
            padding: "8px 14px", fontSize: 12.5, fontWeight: tab===id?600:500,
            color: tab===id?"var(--ink)":"var(--ink-3)",
            borderBottom: `2px solid ${tab===id?"var(--signal)":"transparent"}`, background: "transparent", cursor:"pointer"
          }}>{l} <span className="mono" style={{ color: "var(--ink-4)", fontSize: 10, marginLeft: 4 }}>({n})</span></button>
        ))}
      </div>

      {tab === "circ" && (
        <div className="panel">
          <table className="dtable">
            <thead>
              <tr>
                <th>Date</th>
                <th>Circular</th>
                <th>Dept</th>
                <th>Impact</th>
                <th>Deadline</th>
                <th>Teams</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {circ.map(c => (
                <tr key={c.id} onClick={() => onRoute("library")} style={{ cursor: "pointer" }}>
                  <td className="mono tnum" style={{ whiteSpace: "nowrap", fontSize: 11 }}>{c.date}</td>
                  <td>
                    <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{c.num}</div>
                    <div style={{ fontSize: 13, fontWeight: 500, marginTop: 2, maxWidth: 520 }}>{c.title}</div>
                    {c.summary && <div className="serif" style={{ fontSize: 12.5, fontStyle: "italic", color: "var(--ink-3)", marginTop: 4, maxWidth: 520 }}>{c.summary}</div>}
                  </td>
                  <td style={{ fontSize: 11.5, color: "var(--ink-3)" }}>{c.dept}</td>
                  <td><Pill tone={c.impact==="high"?"amber":c.impact==="med"?"warn":"ghost"}>{c.impact.toUpperCase()}</Pill></td>
                  <td className="mono" style={{ fontSize: 11 }}>{c.deadline || "—"}</td>
                  <td><div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>{(c.teams||[]).slice(0,2).map(t => <Pill key={t} tone="ghost">{t}</Pill>)}</div></td>
                  <td><Icon.Arrow style={{ color: "var(--ink-4)" }} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "news" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {news.map((n, i) => (
            <div key={i} className="panel" style={{ padding: 14, display: "grid", gridTemplateColumns: "1fr auto", gap: 14 }}>
              <div>
                <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6 }}>
                  <Pill tone="blue">{n.src}</Pill>
                  {n.linked && <Pill tone="amber">Linked to circular</Pill>}
                  <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{n.when}</span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.3 }}>{n.title}</div>
              </div>
              <div style={{ textAlign: "right" }}>
                <div className="mono tnum" style={{ fontSize: 18, fontWeight: 600, color: "var(--signal)" }}>{n.relevance}</div>
                <div className="mono up" style={{ fontSize: 9, color: "var(--ink-4)" }}>RELEVANCE</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {tab === "cons" && (
        <div className="panel" style={{ padding: 40, textAlign: "center" }}>
          <Icon.Pulse style={{ color: "var(--ink-4)", width: 32, height: 32 }} />
          <div style={{ marginTop: 10, fontSize: 13, color: "var(--ink-3)" }}>3 open consultations · <a style={{ color: "var(--signal)" }}>view on RBI site</a></div>
        </div>
      )}
    </div>
  );
}

function Library({ onRoute }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const rows = RP_DATA.circulars.filter(c => (filter === "all" || c.impact === filter) && (query === "" || c.title.toLowerCase().includes(query.toLowerCase())));
  return (
    <div style={{ display: "grid", gridTemplateColumns: "240px 1fr", height: "100%" }}>
      <aside style={{ borderRight: "1px solid var(--line)", background: "var(--panel)", padding: "18px 16px", overflowY: "auto" }}>
        <div className="tick" style={{ marginBottom: 10 }}>FILTERS</div>
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 6 }}>IMPACT</div>
        {[["all","All"],["high","High"],["med","Medium"],["low","Low"]].map(([k,l]) => (
          <label key={k} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 12.5, cursor: "pointer" }}>
            <input type="radio" checked={filter===k} onChange={() => setFilter(k)} className="checkbox" style={{ borderRadius: "50%" }} />
            {l}
          </label>
        ))}
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}>DEPARTMENT</div>
        {["Dept. of Regulation","Foreign Exchange","DPSS","Consumer Education"].map(d => (
          <label key={d} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 12.5, cursor: "pointer" }}>
            <input type="checkbox" className="checkbox" defaultChecked={d.startsWith("Dept")} /> {d}
          </label>
        ))}
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}>DATE</div>
        {["Last 7 days","Last 30 days","FY26","FY25"].map(d => (
          <label key={d} style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 12.5, cursor: "pointer" }}>
            <input type="checkbox" className="checkbox" /> {d}
          </label>
        ))}
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", margin: "14px 0 6px" }}>STATUS</div>
        <label style={{ display: "flex", alignItems: "center", gap: 8, padding: "3px 0", fontSize: 12.5, cursor: "pointer" }}>
          <input type="checkbox" className="checkbox" defaultChecked /> Active only
        </label>
      </aside>
      <div style={{ padding: "20px 24px", overflowY: "auto" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <h1 className="serif" style={{ fontSize: 26, fontWeight: 400 }}>Circular Library</h1>
          <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>{RP_DATA.pulse.totalCirculars.toLocaleString()} indexed · {RP_DATA.pulse.superseded} superseded this week</span>
          <div style={{ flex: 1 }} />
          <div style={{ display: "flex", alignItems: "center", gap: 8, border: "1px solid var(--line)", background: "var(--panel)", padding: "6px 10px", borderRadius: 3, minWidth: 320 }}>
            <Icon.Search style={{ color: "var(--ink-4)" }} />
            <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search circular number, title, section..."
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 12.5 }} />
          </div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          {rows.map(c => <CircCard key={c.id} c={c} onRoute={onRoute} />)}
        </div>
      </div>
    </div>
  );
}

function CircCard({ c, onRoute }) {
  return (
    <div onClick={() => onRoute("ask")} className="panel" style={{ padding: 14, cursor: "pointer", transition: "border-color .12s" }}
      onMouseOver={e => e.currentTarget.style.borderColor = "var(--ink-4)"}
      onMouseOut={e => e.currentTarget.style.borderColor = "var(--line)"}>
      <div style={{ display: "flex", gap: 6, marginBottom: 8, alignItems: "center" }}>
        <Pill tone={c.impact === "high" ? "amber" : c.impact === "med" ? "warn" : "ghost"}>{c.impact.toUpperCase()}</Pill>
        {c.status === "superseded" && <Pill tone="bad">SUPERSEDED</Pill>}
        <span style={{ flex: 1 }} />
        <span className="mono tnum" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{c.date}</span>
      </div>
      <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)", marginBottom: 4 }}>{c.num}</div>
      <div style={{ fontSize: 13, fontWeight: 500, lineHeight: 1.3, marginBottom: 8, color: "var(--ink)" }}>{c.title}</div>
      {c.summary && <div className="serif" style={{ fontSize: 12.5, fontStyle: "italic", color: "var(--ink-3)", lineHeight: 1.4, marginBottom: 10 }}>{c.summary}</div>}
      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
        {c.tags.map(t => <Pill key={t} tone="ghost">{t}</Pill>)}
      </div>
    </div>
  );
}

function ActionItems() {
  const toast = useToast();
  const [items, setItems] = useState(RP_DATA.actionItems);
  const [filter, setFilter] = useState("all");
  const shown = items.filter(i => filter === "all" ? true : filter === "open" ? i.status !== "done" : i.status === filter);
  const toggle = (id) => setItems(prev => prev.map(i => i.id === id ? { ...i, status: i.status === "done" ? "pending" : i.status === "pending" ? "in-progress" : "done" } : i));

  const stats = {
    total: items.length,
    done: items.filter(i => i.status === "done").length,
    high: items.filter(i => i.priority === "high" && i.status !== "done").length,
    overdue: 1,
  };

  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 14, marginBottom: 16 }}>
        <div>
          <h1 className="serif" style={{ fontSize: 28, fontWeight: 400 }}>Action Items</h1>
          <p className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-3)", marginTop: 4 }}>
            Tasks extracted from briefs and circulars — assigned to teams, tracked to close.
          </p>
        </div>
        <div style={{ flex: 1 }} />
        <MiniStat label="OPEN" value={stats.total - stats.done} />
        <MiniStat label="HIGH" value={stats.high} signal />
        <MiniStat label="OVERDUE" value={stats.overdue} tone="bad" />
        <Btn variant="primary"><Icon.Plus/> New action</Btn>
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 14, borderBottom: "1px solid var(--line)" }}>
        {[["all","All",items.length],["open","Open", items.filter(i=>i.status!=="done").length],["in-progress","In progress", items.filter(i=>i.status==="in-progress").length],["pending","Pending", items.filter(i=>i.status==="pending").length],["done","Done", items.filter(i=>i.status==="done").length]].map(([k,l,n]) => (
          <button key={k} onClick={() => setFilter(k)} style={{
            padding: "7px 12px", fontSize: 12, fontWeight: filter===k?600:400,
            color: filter===k?"var(--ink)":"var(--ink-3)",
            borderBottom: `2px solid ${filter===k?"var(--signal)":"transparent"}`,
            background:"transparent", cursor:"pointer"
          }}>{l} <span className="mono" style={{ color: "var(--ink-4)", fontSize: 10 }}>{n}</span></button>
        ))}
      </div>

      <div className="panel">
        <table className="dtable">
          <thead>
            <tr>
              <th style={{ width: 32 }}></th>
              <th style={{ width: 60 }}>Prio</th>
              <th>Title</th>
              <th style={{ width: 100 }}>Team</th>
              <th style={{ width: 70 }}>Owner</th>
              <th style={{ width: 100 }}>Due</th>
              <th style={{ width: 120 }}>Source</th>
              <th style={{ width: 80 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {shown.map(i => (
              <tr key={i.id}>
                <td><input type="checkbox" className="checkbox" checked={i.status === "done"} onChange={() => toggle(i.id)} /></td>
                <td><Pill tone={i.priority==="high"?"bad":i.priority==="med"?"warn":"ghost"}>{i.priority.toUpperCase()}</Pill></td>
                <td style={{ fontSize: 13, fontWeight: 500, textDecoration: i.status === "done" ? "line-through" : "none", color: i.status === "done" ? "var(--ink-4)" : "var(--ink)" }}>{i.title}</td>
                <td className="mono" style={{ fontSize: 11 }}>{i.team}</td>
                <td><Avatar initials={i.owner} size={22} /></td>
                <td className="mono tnum" style={{ fontSize: 11 }}>{i.due}</td>
                <td><span className="mono" style={{ fontSize: 10.5, color: "var(--signal)" }}>{i.src}</span></td>
                <td><Pill tone={i.status==="done"?"good":i.status==="in-progress"?"amber":"ghost"}>{i.status.replace("-"," ").toUpperCase()}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MiniStat({ label, value, signal, tone }) {
  const color = tone === "bad" ? "var(--bad)" : signal ? "var(--signal)" : "var(--ink)";
  return (
    <div style={{ textAlign: "right", borderRight: "1px solid var(--line)", paddingRight: 14, paddingLeft: 14 }}>
      <div className="tnum" style={{ fontSize: 22, fontWeight: 600, color, letterSpacing: "-0.02em", lineHeight: 1 }}>{value}</div>
      <div className="mono up" style={{ fontSize: 9.5, color: "var(--ink-4)", marginTop: 3 }}>{label}</div>
    </div>
  );
}

function History({ onRoute }) {
  const items = RP_DATA.history;
  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <h1 className="serif" style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}>History</h1>
      <p className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-3)", marginBottom: 16 }}>
        Every question you've asked — with confidence, risk, and teams affected.
      </p>
      <div className="panel">
        <table className="dtable">
          <thead>
            <tr>
              <th>Question</th>
              <th style={{ width: 120 }}>When</th>
              <th style={{ width: 70 }}>Risk</th>
              <th style={{ width: 120 }}>Confidence</th>
              <th style={{ width: 180 }}>Teams</th>
              <th style={{ width: 80 }}></th>
            </tr>
          </thead>
          <tbody>
            {items.map(i => (
              <tr key={i.id} onClick={() => onRoute("ask")} style={{ cursor: "pointer" }}>
                <td style={{ fontSize: 13, fontWeight: 500, maxWidth: 500 }}>{i.q}</td>
                <td className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>{i.when}</td>
                <td><Pill tone={i.risk==="high"?"bad":i.risk==="med"?"warn":"good"}>{i.risk.toUpperCase()}</Pill></td>
                <td>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <div className="bar" style={{ flex: 1 }}><span style={{ width: `${i.conf*100}%`, background: i.conf > 0.7 ? "var(--good)" : i.conf > 0.5 ? "var(--warn)" : "var(--bad)" }}/></div>
                    <span className="mono tnum" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{Math.round(i.conf*100)}%</span>
                  </div>
                </td>
                <td><div style={{ display: "flex", gap: 3, flexWrap: "wrap" }}>{i.teams.map(t => <Pill key={t} tone="ghost">{t}</Pill>)}</div></td>
                <td><Icon.Arrow style={{ color: "var(--ink-4)" }} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Saved({ onRoute }) {
  const items = RP_DATA.saved;
  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <h1 className="serif" style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}>Saved Interpretations</h1>
      <p className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-3)", marginBottom: 16 }}>
        Briefs you've bookmarked for fast recall during board and regulator reviews.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {items.map(s => (
          <div key={s.id} className="panel" style={{ padding: 14, cursor: "pointer" }} onClick={() => onRoute("ask")}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
              <Icon.Bookmark style={{ color: "var(--signal)" }} />
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{s.when}</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 500, lineHeight: 1.3, marginBottom: 6 }}>{s.title}</div>
            <div className="serif" style={{ fontSize: 12.5, fontStyle: "italic", color: "var(--ink-3)", marginBottom: 10 }}>"{s.q}"</div>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              {s.tags.map(t => <Pill key={t} tone="ghost">{t}</Pill>)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Learnings() {
  const items = RP_DATA.learnings;
  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
        <h1 className="serif" style={{ fontSize: 28, fontWeight: 400 }}>Team Learnings</h1>
        <span className="live-dot" />
      </div>
      <p className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-3)", marginBottom: 20 }}>
        The institutional memory of your compliance team — one-line takeaways, pinned from briefs, shared with the team.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 20 }}>
        <MiniStat label="CAPTURED · TOTAL" value="96"/>
        <MiniStat label="THIS WEEK" value="14" signal />
        <MiniStat label="CONTRIBUTORS" value="5"/>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map(l => (
          <div key={l.id} className="panel" style={{ padding: 14, display: "grid", gridTemplateColumns: "60px 1fr auto", gap: 14, alignItems: "start" }}>
            <div style={{ textAlign: "center" }}>
              <Avatar initials={l.by} size={32} tone={l.by === "PM" ? "signal" : "default"} />
              <div className="mono" style={{ fontSize: 9.5, color: "var(--ink-4)", marginTop: 4 }}>{l.when}</div>
            </div>
            <div>
              <div className="serif" style={{ fontSize: 16, lineHeight: 1.35, color: "var(--ink)", marginBottom: 6 }}>
                <Icon.Spark style={{ color: "var(--signal)", display: "inline", marginRight: 6, verticalAlign: "baseline" }} />
                {l.title}
              </div>
              {l.note && <div className="serif" style={{ fontSize: 13, fontStyle: "italic", color: "var(--ink-3)", lineHeight: 1.5, marginBottom: 8 }}>{l.note}</div>}
              <div style={{ display: "flex", gap: 5, alignItems: "center", flexWrap: "wrap" }}>
                {l.tags.map(t => <Pill key={t} tone="ghost">#{t}</Pill>)}
                <span style={{ color: "var(--ink-4)" }}>·</span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--signal)" }}>Source: {l.src.toUpperCase()}</span>
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <Btn size="sm" variant="ghost"><Icon.Pin /> Pin</Btn>
              <Btn size="sm" variant="ghost">Edit</Btn>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Debate() {
  const threads = [
    { title: "Leverage cap — does de-recognised securitised pool count?", src: "SBR Revision · DOR.CAP.REC.22", replies: 4, stance: { agree: 2, disagree: 2 }, open: true },
    { title: "Video-KYC liveness — applies to routine re-KYC or only OVD refresh?", src: "KYC Amendment · DOR.AML.REC.18", replies: 5, stance: { agree: 1, disagree: 3 }, open: true },
    { title: "PSL climate-adaptive — does cooperative lending qualify?", src: "PSL Targets · DOR.PSL.REC.07", replies: 3, stance: { agree: 3, disagree: 0 }, open: false },
    { title: "ECB fallback — retro-execution of SOFR amendment", src: "ECB · FED.FE.REC.09", replies: 2, stance: { agree: 2, disagree: 0 }, open: false },
  ];
  return (
    <div style={{ padding: "20px 24px 60px" }}>
      <h1 className="serif" style={{ fontSize: 28, fontWeight: 400, marginBottom: 4 }}>Debates</h1>
      <p className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-3)", marginBottom: 20 }}>
        Where your team's disagreements become a record — annotate briefs, argue the interpretation, let the strongest reading win.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {threads.map((t, i) => {
          const tot = t.stance.agree + t.stance.disagree;
          return (
            <div key={i} className="panel" style={{ padding: 16 }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                <Pill tone={t.open ? "amber" : "good"}>{t.open ? "OPEN" : "RESOLVED"}</Pill>
                <Pill tone="ghost">{t.replies} replies</Pill>
              </div>
              <div style={{ fontSize: 14.5, fontWeight: 500, lineHeight: 1.3, marginBottom: 6 }}>{t.title}</div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)", marginBottom: 12 }}>{t.src}</div>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                <div style={{ flex: 1, height: 5, borderRadius: 3, overflow: "hidden", background: "var(--line)", display: "flex" }}>
                  <div style={{ width: `${t.stance.agree/tot*100}%`, background: "var(--good)" }}/>
                  <div style={{ width: `${t.stance.disagree/tot*100}%`, background: "var(--bad)" }}/>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11 }}>
                <span className="mono" style={{ color: "var(--good)" }}>▲ {t.stance.agree} agree</span>
                <span className="mono" style={{ color: "var(--bad)" }}>▼ {t.stance.disagree} disagree</span>
                <div style={{ flex: 1 }} />
                <Btn size="sm" variant="ghost">Open thread <Icon.Arrow /></Btn>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Upgrade() {
  const plans = [
    { name: "Free", price: "₹0", sub: "forever", features: ["5 questions / mo", "Basic citations", "Single user"], cta: "Current", current: true },
    { name: "Pro", price: "₹2,400", sub: "/ user / mo", features: ["Unlimited questions", "PDF briefing exports", "Team learnings", "Debates & annotations", "Priority support"], cta: "Upgrade", featured: true },
    { name: "Enterprise", price: "Custom", sub: "billed annually", features: ["Everything in Pro", "Workflow integrations", "Custom ingestion (internal memos)", "Dedicated reviewer", "SSO & SCIM", "DPDP deletion workflow"], cta: "Talk to sales" },
  ];
  return (
    <div style={{ padding: "30px 24px 60px", maxWidth: 1100, margin: "0 auto" }}>
      <div className="serif" style={{ fontSize: 36, fontWeight: 400, letterSpacing: "-0.02em", lineHeight: 1.1, marginBottom: 10, textAlign: "center" }}>
        The fastest path from circular to board briefing.
      </div>
      <p className="serif" style={{ fontSize: 16, fontStyle: "italic", color: "var(--ink-3)", textAlign: "center", marginBottom: 36 }}>
        Pro plans pay for themselves the first time you catch a 10 bps miss before the regulator does.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        {plans.map(p => (
          <div key={p.name} className="panel" style={{ padding: 24, position: "relative", borderColor: p.featured ? "var(--signal)" : "var(--line)", borderWidth: p.featured ? 2 : 1, borderStyle: "solid" }}>
            {p.featured && (
              <div className="mono" style={{ position: "absolute", top: -10, left: 20, background: "var(--signal)", color: "#fff", padding: "3px 10px", fontSize: 10, fontWeight: 600, borderRadius: 2, letterSpacing: ".08em" }}>
                MOST CHOSEN
              </div>
            )}
            <div className="mono up" style={{ fontSize: 11, color: "var(--ink-4)", marginBottom: 8 }}>{p.name.toUpperCase()}</div>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 20 }}>
              <span className="tnum" style={{ fontSize: 38, fontWeight: 600, letterSpacing: "-0.02em" }}>{p.price}</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>{p.sub}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
              {p.features.map(f => (
                <div key={f} style={{ display: "flex", gap: 8, fontSize: 13, color: "var(--ink-2)", alignItems: "flex-start" }}>
                  <Icon.Check style={{ color: "var(--good)", marginTop: 2, flexShrink: 0 }} /> {f}
                </div>
              ))}
            </div>
            <Btn variant={p.featured ? "accent" : p.current ? "" : "primary"} disabled={p.current} style={{ width: "100%", justifyContent: "center", padding: "10px" }}>
              {p.cta}
            </Btn>
          </div>
        ))}
      </div>
    </div>
  );
}

function Account() {
  const u = RP_DATA.user;
  return (
    <div style={{ padding: "20px 24px 60px", maxWidth: 900 }}>
      <h1 className="serif" style={{ fontSize: 28, fontWeight: 400, marginBottom: 20 }}>Account</h1>
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>PROFILE</div>
        <div style={{ display: "grid", gridTemplateColumns: "120px 1fr", gap: 10, fontSize: 13 }}>
          <div style={{ color: "var(--ink-4)" }}>Name</div><div>{u.name}</div>
          <div style={{ color: "var(--ink-4)" }}>Email</div><div className="mono">{u.email}</div>
          <div style={{ color: "var(--ink-4)" }}>Role</div><div>{u.role}</div>
          <div style={{ color: "var(--ink-4)" }}>Organisation</div><div>{u.org}</div>
          <div style={{ color: "var(--ink-4)" }}>Plan</div><div><Pill tone="amber">{u.plan.toUpperCase()}</Pill></div>
        </div>
      </div>
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>TEAM · 5 MEMBERS</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {[
            { i: "PM", n: "Priya Menon", r: "CCO" },
            { i: "RK", n: "Raghav Krishnan", r: "Head, Risk" },
            { i: "AS", n: "Anjali Shah", r: "Treasury" },
            { i: "VN", n: "Vikram Nair", r: "Compliance Lead" },
            { i: "DK", n: "Divya Kapoor", r: "Capital Strategy" },
          ].map(m => (
            <div key={m.i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Avatar initials={m.i} size={26} tone={m.i === "PM" ? "signal" : "default"} />
              <div style={{ fontSize: 13, fontWeight: 500 }}>{m.n}</div>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{m.r}</div>
              <div style={{ flex: 1 }} />
              <Btn size="sm" variant="ghost">Permissions</Btn>
            </div>
          ))}
        </div>
      </div>
      <div className="panel" style={{ padding: 20, marginBottom: 16 }}>
        <div className="tick" style={{ marginBottom: 14 }}>DATA · DPDP COMPLIANCE</div>
        <div style={{ display: "flex", gap: 10, fontSize: 12.5, color: "var(--ink-3)", marginBottom: 12 }}>
          You have the right to export or delete your data at any time under the DPDP Act.
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn>Export my data</Btn>
          <Btn variant="ghost" style={{ color: "var(--bad)" }}>Delete account</Btn>
        </div>
      </div>
    </div>
  );
}

function Admin() {
  const [sub, setSub] = useState("dashboard");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", height: "100%", overflow: "hidden" }}>
      <aside style={{ borderRight: "1px solid var(--line)", background: "var(--panel)", padding: "16px 0" }}>
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", padding: "4px 16px 8px" }}>ADMIN</div>
        {[["dashboard","Overview"],["review","Review Queue"],["prompts","Prompts"],["users","Users"],["circulars","Circulars"],["scraper","Scraper"],["heatmap","Clustering"]].map(([k,l]) => (
          <div key={k} onClick={() => setSub(k)} style={{
            padding: "7px 16px", fontSize: 12.5, cursor: "pointer",
            color: sub === k ? "var(--ink)" : "var(--ink-3)",
            background: sub === k ? "var(--panel-2)" : "transparent",
            borderLeft: `2px solid ${sub === k ? "var(--signal)" : "transparent"}`,
            fontWeight: sub === k ? 600 : 400,
          }}>{l}</div>
        ))}
      </aside>
      <div style={{ overflowY: "auto", padding: "20px 24px 60px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <h1 className="serif" style={{ fontSize: 26, fontWeight: 400 }}>Admin · Overview</h1>
          <Pill tone="bad">ADMIN MODE</Pill>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          <MetricTile label="ACTIVE USERS" value="142" delta="+8" trend="up" sparkline={[120,125,130,128,134,138,140,142]} />
          <MetricTile label="QUESTIONS · WK" value="1,842" delta="+142" trend="up" sparkline={[200,220,250,240,280,300,320,350]} />
          <MetricTile label="REVIEW QUEUE" value="12" delta="-3" trend="down" sparkline={[18,16,14,13,15,13,12,12]} signal />
          <MetricTile label="LLM COST · WK" value="$84.20" delta="+$6" trend="up" sparkline={[70,72,74,76,80,82,83,84]} />
        </div>
        <div className="panel">
          <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)" }}>
            <div className="tick">SCRAPER · LAST 24H</div>
          </div>
          <div style={{ padding: 16 }}>
            <div style={{ display: "grid", gridTemplateColumns: "auto 1fr auto", gap: 10, alignItems: "center" }}>
              <span className="live-dot" />
              <span style={{ fontSize: 12.5 }}>Celery beat · running</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>next run in 18m</span>
              <div style={{ width: 8 }}/>
              <div />
              <div />
              <Icon.Check style={{ color: "var(--good)" }} />
              <span style={{ fontSize: 12.5 }}>Daily scrape · 14 new docs · 2 superseded</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>2h ago</span>
              <Icon.Check style={{ color: "var(--good)" }} />
              <span style={{ fontSize: 12.5 }}>Embeddings · 1,204 chunks · 4.1s avg</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>2h ago</span>
              <Icon.Check style={{ color: "var(--good)" }} />
              <span style={{ fontSize: 12.5 }}>KG expansion · 38 entities, 62 relationships</span>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-3)" }}>2h ago</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { Updates, Library, ActionItems, History, Saved, Learnings, Debate, Upgrade, Account, Admin });
