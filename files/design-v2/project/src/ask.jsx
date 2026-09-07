// Ask — editorial brief view with annotations, feedback, save-as-learning, debate

function Ask({ onRoute }) {
  const toast = useToast();
  const a = RP_DATA.featuredAnswer;
  const [q, setQ] = useState(a.question);
  const [state, setState] = useState("answered"); // idle | streaming | answered
  const [streamed, setStreamed] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(0);
  const [thumb, setThumb] = useState(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [savedAsLearning, setSavedAsLearning] = useState(false);
  const [learningNote, setLearningNote] = useState("");
  const [showLearningModal, setShowLearningModal] = useState(false);
  const [annotations, setAnnotations] = useState([
    { id: "a1", text: "10% effective 1 April 2027", note: "Board already assumed 9.5% — reconfirm with Vijay.", by: "PM", when: "12m" },
  ]);
  const [activeAnnot, setActiveAnnot] = useState(null);

  const streaming = state === "streaming";

  const submit = () => {
    setState("streaming");
    setStreamed("");
    let i = 0;
    const fullText = a.body.map(p => p.text).join("");
    const id = setInterval(() => {
      i += 8;
      if (i >= fullText.length) { clearInterval(id); setState("answered"); setStreamed(null); return; }
      setStreamed(fullText.slice(0, i));
    }, 18);
  };

  const saveLearning = () => {
    setSavedAsLearning(true);
    setShowLearningModal(false);
    toast.push({ tag: "LEARNING", text: "Saved to team library. Raghav & Anjali notified." });
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", height: "100%", overflow: "hidden" }}>
      {/* Main column */}
      <div style={{ overflowY: "auto", padding: "20px 28px 60px" }}>

        {/* Question bar */}
        <div className="panel" style={{ padding: "14px 16px", marginBottom: 20 }}>
          <div className="tick" style={{ marginBottom: 8 }}>ASK · RETRIEVAL FROM 4,821 CIRCULARS · KG-EXPANSION ON</div>
          <div style={{ display: "flex", gap: 8 }}>
            <textarea
              value={q}
              onChange={(e) => setQ(e.target.value)}
              className="input"
              style={{ flex: 1, minHeight: 54, fontFamily: "var(--font-serif)", fontSize: 15, lineHeight: 1.5 }}
            />
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <Btn variant="accent" onClick={submit} disabled={streaming}>
                {streaming ? "Thinking…" : "Ask"} <Icon.Arrow />
              </Btn>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", textAlign: "center" }}>
                1 credit
              </div>
            </div>
          </div>
        </div>

        {/* Editorial answer */}
        <div style={{ position: "relative" }}>
          {/* Byline */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <div className="mono up" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>BRIEF · {a.id.toUpperCase()}</div>
            <span style={{ width: 1, height: 10, background: "var(--line)" }} />
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Avatar initials={RP_DATA.user.initials} size={20} tone="signal" />
              <span style={{ fontSize: 12, color: "var(--ink-2)" }}>{a.askedBy}</span>
              <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>· {a.askedAt}</span>
            </div>
            <div style={{ flex: 1 }} />
            <Pill tone="bad"><Icon.Flag style={{ width: 10, height: 10 }}/> RISK HIGH</Pill>
            <ConfBadge score={a.confidence} />
          </div>

          {/* Question headline */}
          <h2 className="serif" style={{ fontSize: 32, fontWeight: 400, lineHeight: 1.15, letterSpacing: "-0.015em", marginBottom: 18, color: "var(--ink)" }}>
            {a.question}
          </h2>

          {/* Body */}
          <div className="prose" style={{ maxWidth: 680 }}>
            <p className="dek">{a.dek}</p>
            {streaming ? (
              <p>{streamed}<span className="live-dot" style={{ marginLeft: 6, verticalAlign: "middle" }} /></p>
            ) : (
              a.body.map((chunk, i) => chunk.annot ? (
                <AnnotSpan key={i} id={chunk.annotId} text={chunk.text} annots={annotations} setActive={setActiveAnnot} />
              ) : (
                <span key={i}>{chunk.text}</span>
              ))
            )}
          </div>

          {/* Recommended actions */}
          <div style={{ marginTop: 32 }}>
            <div className="tick" style={{ marginBottom: 10 }}>RECOMMENDED ACTIONS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {a.actions.map((ac, i) => (
                <div key={i} style={{
                  display: "grid", gridTemplateColumns: "56px 120px 1fr 70px auto", gap: 12,
                  padding: "12px 14px", border: "1px solid var(--line)", background: "var(--bg)",
                  borderRadius: 3, alignItems: "center",
                }}>
                  <Pill tone={ac.priority === "high" ? "bad" : ac.priority === "med" ? "warn" : "ghost"}>
                    {ac.priority.toUpperCase()}
                  </Pill>
                  <div className="mono" style={{ fontSize: 11, color: "var(--ink-2)", fontWeight: 600 }}>{ac.team}</div>
                  <div style={{ fontSize: 13, lineHeight: 1.4 }}>{ac.text}</div>
                  <div className="mono tnum" style={{ fontSize: 11, color: "var(--ink-3)" }}>Due {ac.due}</div>
                  <Btn size="sm" variant="ghost" onClick={() => toast.push({ tag: "ACTION", text: `Assigned to ${ac.team}.` })}>
                    <Icon.Plus /> Task
                  </Btn>
                </div>
              ))}
            </div>
          </div>

          {/* Feedback bar */}
          <div style={{ marginTop: 32, padding: "14px 16px", border: "1px solid var(--line)", borderRadius: 3, background: "var(--panel-2)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap" }}>
              <div style={{ fontSize: 12.5, color: "var(--ink-2)", flex: "0 0 auto" }}>
                <b>Was this brief accurate and useful?</b>
              </div>
              <div style={{ display: "flex", gap: 6 }}>
                <Btn variant={thumb === "up" ? "accent" : ""} size="sm" onClick={() => { setThumb("up"); setShowFeedback(true); }}>
                  <Icon.Thumb /> Accurate
                </Btn>
                <Btn variant={thumb === "down" ? "accent" : ""} size="sm" onClick={() => { setThumb("down"); setShowFeedback(true); }}>
                  <Icon.ThumbD /> Needs work
                </Btn>
              </div>
              <div style={{ flex: 1 }} />
              <Btn
                variant={savedAsLearning ? "" : "primary"}
                size="sm"
                onClick={() => setShowLearningModal(true)}>
                <Icon.Spark /> {savedAsLearning ? "Saved as learning" : "Save as team learning"}
              </Btn>
              <Btn variant="ghost" size="sm"><Icon.Bookmark /> Save</Btn>
              <Btn variant="ghost" size="sm" onClick={() => toast.push({ tag: "EXPORT", text: "PDF briefing queued for download." })}>
                Export PDF
              </Btn>
            </div>
            {showFeedback ? (
              <FeedbackForm thumb={thumb} onClose={() => setShowFeedback(false)} onSubmit={() => { setShowFeedback(false); toast.push({ tag: "FEEDBACK", text: "Thanks — routed to the RegPulse review queue." }); }} />
            ) : null}
          </div>

          <BriefFooter />
        </div>
      </div>

      {/* Right rail — citations, confidence, debate */}
      <aside style={{
        borderLeft: "1px solid var(--line)",
        background: "var(--panel)",
        overflowY: "auto",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--line)" }}>
          <div className="tick" style={{ marginBottom: 8 }}>CONFIDENCE</div>
          <ConfidenceRadial score={a.confidence} />
          <div style={{ marginTop: 10, fontSize: 11.5, color: "var(--ink-3)", lineHeight: 1.4 }}>
            High-precision citations, no cross-jurisdiction conflicts, 3 supporting chunks from the canonical circular.
          </div>
        </div>

        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--line)" }}>
          <div className="tick" style={{ marginBottom: 10 }}>CITATIONS · {a.citations.length}</div>
          {a.citations.map((c, i) => (
            <div key={i}
              onClick={() => setSelectedCitation(i)}
              style={{
                padding: "10px 12px", marginBottom: 6, cursor: "pointer", borderRadius: 2,
                border: `1px solid ${selectedCitation === i ? "var(--signal)" : "var(--line)"}`,
                background: selectedCitation === i ? "var(--signal-bg)" : "var(--bg)",
                transition: "border-color .12s, background .12s",
              }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <span className="mono" style={{ fontSize: 10, fontWeight: 600, color: "var(--signal)" }}>[{i+1}]</span>
                <span className="mono" style={{ fontSize: 10.5, color: "var(--ink-3)" }}>{c.section}</span>
              </div>
              <div className="serif" style={{ fontSize: 12.5, fontStyle: "italic", color: "var(--ink-2)", lineHeight: 1.45 }}>
                “{c.quote}”
              </div>
              <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 6 }}>{c.num}</div>
            </div>
          ))}
        </div>

        <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--line)" }}>
          <div className="tick" style={{ marginBottom: 10 }}>DEBATE · {a.debate.length}</div>
          {a.debate.map((d, i) => (
            <div key={i} style={{ padding: "10px 0", borderBottom: i === a.debate.length - 1 ? "none" : "1px solid var(--line)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <Avatar initials={d.who} size={18} tone={d.who === "PM" ? "signal" : "default"} />
                <span style={{ fontSize: 11.5, fontWeight: 600 }}>{d.who}</span>
                <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{d.role}</span>
                <span style={{ flex: 1 }} />
                <span className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{d.when}</span>
              </div>
              <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.45 }}>{d.text}</div>
            </div>
          ))}
          <div style={{ marginTop: 10, display: "flex", gap: 6 }}>
            <input className="input" placeholder="Add to debate…" style={{ fontSize: 12 }} />
            <Btn size="sm" variant="primary">Post</Btn>
          </div>
        </div>

        <div style={{ padding: "14px 16px", background: "var(--bg-1)", marginTop: "auto" }}>
          <div className="tick" style={{ marginBottom: 8 }}>ANNOTATIONS · {annotations.length}</div>
          <div style={{ fontSize: 11.5, color: "var(--ink-3)", lineHeight: 1.5 }}>
            Select any passage in the brief to annotate. Margin notes are visible only to your team.
          </div>
        </div>
      </aside>

      {showLearningModal ? (
        <LearningModal
          question={a.question}
          note={learningNote}
          setNote={setLearningNote}
          onSave={saveLearning}
          onClose={() => setShowLearningModal(false)}
        />
      ) : null}

      {activeAnnot ? (
        <AnnotPopover annot={annotations.find(x => x.id === activeAnnot)} onClose={() => setActiveAnnot(null)} />
      ) : null}
    </div>
  );
}

function AnnotSpan({ id, text, annots, setActive }) {
  const has = annots.some(a => a.id === id);
  return (
    <mark
      className="annot"
      onClick={() => setActive(id)}
      style={{ position: "relative" }}>
      {text}
      {has ? <sup className="mono" style={{ marginLeft: 2, fontSize: 9, color: "var(--signal)", fontWeight: 700 }}>§</sup> : null}
    </mark>
  );
}

function AnnotPopover({ annot, onClose }) {
  if (!annot) return null;
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(0,0,0,0.2)" }}>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          position: "absolute", top: "30%", left: "35%",
          width: 360, background: "var(--panel)",
          border: "1px solid var(--line-2)", boxShadow: "var(--shadow-lg)",
          borderRadius: 4, padding: 16,
        }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Avatar initials={annot.by} size={22} tone="signal" />
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 600 }}>{annot.by}</div>
            <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)" }}>{annot.when} ago · on “{annot.text}”</div>
          </div>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" icon onClick={onClose}><Icon.Close/></Btn>
        </div>
        <div className="serif" style={{ fontSize: 14, fontStyle: "italic", lineHeight: 1.5, color: "var(--ink-2)", borderLeft: "2px solid var(--signal)", paddingLeft: 10 }}>
          {annot.note}
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
          <Btn size="sm"><Icon.Plus /> Reply</Btn>
          <Btn variant="ghost" size="sm">Resolve</Btn>
        </div>
      </div>
    </div>
  );
}

function ConfBadge({ score }) {
  const pct = Math.round(score * 100);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--ink-3)" }}>
      <span className="mono up">CONF</span>
      <span className="mono tnum" style={{ fontWeight: 600, color: "var(--ink)" }}>{pct}%</span>
      <div style={{ width: 40 }}>
        <div className="bar good"><span style={{ width: `${pct}%` }}/></div>
      </div>
    </div>
  );
}

function ConfidenceRadial({ score }) {
  const pct = Math.round(score * 100);
  const r = 32;
  const c = 2 * Math.PI * r;
  const off = c - (c * pct) / 100;
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <svg width="84" height="84" viewBox="0 0 84 84" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="42" cy="42" r={r} stroke="var(--line)" strokeWidth="6" fill="none" />
        <circle cx="42" cy="42" r={r} stroke="var(--signal)" strokeWidth="6" fill="none" strokeLinecap="butt"
                strokeDasharray={c} strokeDashoffset={off} />
      </svg>
      <div>
        <div className="tnum" style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.02em", lineHeight: 1 }}>{pct}<span style={{ fontSize: 14, color: "var(--ink-4)" }}>%</span></div>
        <div className="mono up" style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 4 }}>HIGH CONFIDENCE</div>
      </div>
    </div>
  );
}

function FeedbackForm({ thumb, onClose, onSubmit }) {
  const options = thumb === "down" ? [
    "Missing a relevant circular",
    "Misinterpreted a citation",
    "Risk level too low",
    "Risk level too high",
    "Actions not aligned with our structure",
    "Stale — superseded circular cited",
  ] : [
    "Exactly what I needed",
    "Cited the right sections",
    "Actions are actionable",
    "Confidence feels right",
  ];
  const [checked, setChecked] = useState([]);
  const [note, setNote] = useState("");
  const toggle = (o) => setChecked(c => c.includes(o) ? c.filter(x => x !== o) : [...c, o]);
  return (
    <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--line)" }}>
      <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginBottom: 8 }}>
        {thumb === "down" ? "What's wrong or missing?" : "What worked well?"}
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
        {options.map(o => (
          <label key={o} style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            padding: "4px 8px", fontSize: 11.5,
            border: `1px solid ${checked.includes(o) ? "var(--signal)" : "var(--line)"}`,
            background: checked.includes(o) ? "var(--signal-bg)" : "var(--bg)",
            borderRadius: 2, cursor: "pointer",
            color: checked.includes(o) ? "var(--signal-ink)" : "var(--ink-2)",
          }}>
            <input type="checkbox" checked={checked.includes(o)} onChange={() => toggle(o)} className="checkbox" />
            {o}
          </label>
        ))}
      </div>
      <textarea value={note} onChange={e => setNote(e.target.value)} className="input"
        placeholder="Optional: what should the brief have said?" style={{ minHeight: 60, fontSize: 12.5 }} />
      <div style={{ display: "flex", gap: 6, marginTop: 8, justifyContent: "flex-end" }}>
        <Btn variant="ghost" size="sm" onClick={onClose}>Cancel</Btn>
        <Btn variant="primary" size="sm" onClick={onSubmit}>Send to review queue</Btn>
      </div>
    </div>
  );
}

function LearningModal({ question, note, setNote, onSave, onClose }) {
  const [title, setTitle] = useState("Tier-1 floor for UL NBFCs is 10%, not 9.5% — glide-path ends Q4 FY27.");
  const [tags, setTags] = useState(["SBR", "Tier-1", "FY27"]);
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 90, background: "rgba(0,0,0,0.35)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div onClick={e => e.stopPropagation()} style={{
        width: 560, background: "var(--panel)",
        border: "1px solid var(--line-2)", boxShadow: "var(--shadow-lg)",
        borderRadius: 4, overflow: "hidden",
      }}>
        <div style={{ padding: "14px 18px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
          <Icon.Spark style={{ color: "var(--signal)" }} />
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>Save as team learning</h3>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" icon onClick={onClose}><Icon.Close /></Btn>
        </div>
        <div style={{ padding: 18 }}>
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 4, letterSpacing: ".08em" }}>SOURCE QUESTION</div>
          <div className="serif" style={{ fontSize: 14, fontStyle: "italic", color: "var(--ink-2)", marginBottom: 16, lineHeight: 1.4 }}>
            “{question}”
          </div>
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 4, letterSpacing: ".08em" }}>LEARNING · ONE-LINE TAKEAWAY</div>
          <input className="input" value={title} onChange={e => setTitle(e.target.value)} style={{ marginBottom: 12 }} />
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 4, letterSpacing: ".08em" }}>NOTES (OPTIONAL)</div>
          <textarea className="input" value={note} onChange={e => setNote(e.target.value)}
            placeholder="Context for the team — why this matters, what changed."
            style={{ minHeight: 72, marginBottom: 12 }} />
          <div className="mono" style={{ fontSize: 10, color: "var(--ink-4)", marginBottom: 6, letterSpacing: ".08em" }}>TAGS</div>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
            {tags.map(t => <Pill key={t} tone="amber">{t} <Icon.Close style={{ width: 9, height: 9, marginLeft: 4 }}/></Pill>)}
            <Pill tone="ghost">+ add</Pill>
          </div>
        </div>
        <div style={{ padding: "12px 18px", background: "var(--bg-1)", borderTop: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
          <label style={{ fontSize: 12, color: "var(--ink-3)", display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" className="checkbox" defaultChecked /> Notify team (5 members)
          </label>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" onClick={onClose}>Cancel</Btn>
          <Btn variant="accent" onClick={onSave}><Icon.Spark /> Save learning</Btn>
        </div>
      </div>
    </div>
  );
}

function BriefFooter() {
  return (
    <div style={{ marginTop: 32, padding: "16px 0", borderTop: "1px solid var(--line)", fontSize: 11, color: "var(--ink-4)", lineHeight: 1.6 }}>
      <div className="mono up" style={{ marginBottom: 4 }}>DISCLAIMER</div>
      RegPulse is not a legal advisory service. Briefs are AI-generated from indexed RBI circulars and must be verified at rbi.org.in before action.
    </div>
  );
}

Object.assign(window, { Ask });
