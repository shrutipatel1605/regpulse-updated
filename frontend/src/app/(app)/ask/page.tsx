"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { useAuthStore } from "@/stores/authStore";
import { trackEvent } from "@/lib/analytics";
import { RP_DATA } from "@/lib/mockData";
import { Avatar, Btn, Icon, Pill, useToast } from "@/components/design/Primitives";
import api from "@/lib/api";
import type { CitationItem, RecommendedAction } from "@/types";

/* ── Types ─────────────────────────────────────────────────────────────── */

interface Suggestion {
  id: string;
  question_text: string;
  quick_answer_preview: string | null;
}

interface StreamState {
  status: "idle" | "streaming" | "done" | "error";
  answer: string;
  quickAnswer: string | null;
  riskLevel: string | null;
  confidenceScore: number | null;
  consultExpert: boolean;
  citations: CitationItem[];
  affectedTeams: string[];
  recommendedActions: RecommendedAction[];
  questionId: string | null;
  creditBalance: number | null;
  errorMessage: string | null;
}

const initialState: StreamState = {
  status: "idle",
  answer: "",
  quickAnswer: null,
  riskLevel: null,
  confidenceScore: null,
  consultExpert: false,
  citations: [],
  affectedTeams: [],
  recommendedActions: [],
  questionId: null,
  creditBalance: null,
  errorMessage: null,
};

/* ── Annotation types (mock-only for now) ──────────────────────────────── */

interface Annotation {
  id: string;
  text: string;
  note: string;
  by: string;
  when: string;
}

/* ── Main component ──────────────────────────────────────────────────── */

export default function AskPage() {
  const toast = useToast();
  const fa = RP_DATA.featuredAnswer;

  const [question, setQuestion] = useState("");
  const [state, setState] = useState<StreamState>(initialState);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const suggestionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Editorial brief UI state
  const [selectedCitation, setSelectedCitation] = useState(0);
  const [thumb, setThumb] = useState<"up" | "down" | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [savedAsLearning, setSavedAsLearning] = useState(false);
  const [learningNote, setLearningNote] = useState("");
  const [showLearningModal, setShowLearningModal] = useState(false);
  const [annotations] = useState<Annotation[]>([
    {
      id: "a1",
      text: "10% effective 1 April 2027",
      note: "Board already assumed 9.5% — reconfirm with Vijay.",
      by: "PM",
      when: "12m",
    },
  ]);
  const [activeAnnot, setActiveAnnot] = useState<string | null>(null);

  // ── Suggestions (debounced) ──────────────────────────────────────────
  useEffect(() => {
    if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
    const trimmed = question.trim();
    if (trimmed.length < 5) {
      setSuggestions([]);
      return;
    }
    suggestionTimer.current = setTimeout(async () => {
      try {
        const { data } = await api.get("/questions/suggestions", {
          params: { q: trimmed, limit: 5 },
        });
        setSuggestions(data.data || []);
      } catch {
        setSuggestions([]);
      }
    }, 300);
    return () => {
      if (suggestionTimer.current) clearTimeout(suggestionTimer.current);
    };
  }, [question]);

  const suggestionList = useMemo(
    () => (showSuggestions ? suggestions : []),
    [showSuggestions, suggestions],
  );

  // ── SSE jitter fix: buffer + rAF flush ───────────────────────────────
  const tokenBufferRef = useRef<string>("");
  const flushScheduledRef = useRef(false);
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const flushTokens = useCallback(() => {
    flushScheduledRef.current = false;
    const pending = tokenBufferRef.current;
    if (!pending) return;
    tokenBufferRef.current = "";
    setState((prev) => ({ ...prev, answer: prev.answer + pending }));
  }, []);

  const scheduleFlush = useCallback(() => {
    if (flushScheduledRef.current) return;
    flushScheduledRef.current = true;
    if (typeof requestAnimationFrame === "function") {
      requestAnimationFrame(flushTokens);
    } else {
      setTimeout(flushTokens, 16);
    }
  }, [flushTokens]);

  // ── Submit question via SSE ──────────────────────────────────────────
  const handleAsk = useCallback(async () => {
    if (!question.trim() || question.trim().length < 5) return;
    if (state.status === "streaming") return;

    tokenBufferRef.current = "";
    flushScheduledRef.current = false;
    setState({ ...initialState, status: "streaming" });
    setSelectedCitation(0);
    setThumb(null);
    setShowFeedback(false);
    setSavedAsLearning(false);
    trackEvent("ask_question_submitted", {
      question_length: question.trim().length,
    });

    const controller = new AbortController();
    abortRef.current = controller;

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    try {
      const response = await fetch(`${apiUrl}/questions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        },
        credentials: "include",
        body: JSON.stringify({ question: question.trim() }),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        setState((prev) => ({
          ...prev,
          status: "error",
          errorMessage:
            errorData?.error || `Request failed (${response.status})`,
        }));
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        setState((prev) => ({
          ...prev,
          status: "error",
          errorMessage: "No response body",
        }));
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("event: ")) continue;
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);

              if ("token" in data) {
                tokenBufferRef.current += data.token;
                scheduleFlush();
              } else if ("citations" in data) {
                flushTokens();
                setState((prev) => ({
                  ...prev,
                  citations: data.citations || [],
                  riskLevel: data.risk_level || null,
                  confidenceScore:
                    typeof data.confidence_score === "number"
                      ? data.confidence_score
                      : null,
                  consultExpert: Boolean(data.consult_expert),
                  affectedTeams: data.affected_teams || [],
                  recommendedActions: data.recommended_actions || [],
                  quickAnswer: data.quick_answer || null,
                }));
                trackEvent("confidence_meter_viewed", {
                  confidence_score:
                    typeof data.confidence_score === "number"
                      ? data.confidence_score
                      : null,
                  consult_expert: Boolean(data.consult_expert),
                  source: "ask",
                });
              } else if ("question_id" in data) {
                flushTokens();
                setState((prev) => ({
                  ...prev,
                  status: "done",
                  questionId: data.question_id,
                  creditBalance: data.credit_balance,
                }));
                if (user && data.credit_balance !== undefined) {
                  useAuthStore.setState({
                    user: { ...user, credit_balance: data.credit_balance },
                  });
                }
              } else if ("error" in data) {
                setState((prev) => ({
                  ...prev,
                  status: "error",
                  errorMessage: data.error,
                }));
              }
            } catch {
              // Skip malformed JSON lines
            }
          }
        }
      }

      flushTokens();
      setState((prev) =>
        prev.status === "streaming" ? { ...prev, status: "done" } : prev,
      );
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      setState((prev) => ({
        ...prev,
        status: "error",
        errorMessage: err instanceof Error ? err.message : "Request failed",
      }));
    }
  }, [question, state.status, accessToken, user, flushTokens, scheduleFlush]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleAsk();
      }
    },
    [handleAsk],
  );

  const streaming = state.status === "streaming";
  const hasAnswer =
    (state.status === "streaming" || state.status === "done") &&
    Boolean(state.answer);

  // Whether we're showing the mock featured answer or a live SSE answer
  const showMock = state.status === "idle";

  // Determine display values — mock data when idle, real SSE data when streaming/done
  const displayQuestion = showMock ? fa.question : question;
  const displayConfidence = showMock
    ? fa.confidence
    : state.confidenceScore;
  const displayRisk = showMock ? fa.risk : state.riskLevel;
  const displayCitations = showMock
    ? fa.citations.map((c) => ({
        circular_number: c.num,
        verbatim_quote: c.quote,
        section_reference: c.section,
      }))
    : state.citations;
  const displayActions = showMock
    ? fa.actions.map((a) => ({
        team: a.team,
        action_text: a.text,
        priority: a.priority,
        due: a.due,
      }))
    : state.recommendedActions.map((a) => ({
        ...a,
        due: "",
      }));
  const displayDebate = showMock ? fa.debate : [];

  const saveLearning = () => {
    setSavedAsLearning(true);
    setShowLearningModal(false);
    toast.push({ tag: "LEARNING", text: "Saved to team library. Raghav & Anjali notified." });
  };

  return (
    <div
      className="rp-route-fade"
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 320px",
        height: "100%",
        overflow: "hidden",
      }}
    >
      {/* ── Main column ─────────────────────────────────────────────────── */}
      <div style={{ overflowY: "auto", padding: "20px 28px 60px" }}>
        {/* Question bar */}
        <div className="panel" style={{ padding: "14px 16px", marginBottom: 20 }}>
          <div className="tick" style={{ marginBottom: 8 }}>
            ASK · RETRIEVAL FROM 4,821 CIRCULARS · KG-EXPANSION ON
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <div style={{ flex: 1, position: "relative" }}>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => setShowSuggestions(true)}
                onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
                className="input"
                placeholder="e.g., What are the latest KYC requirements for banks under the SBR framework?"
                style={{
                  flex: 1,
                  minHeight: 54,
                  fontFamily: "var(--font-serif)",
                  fontSize: 15,
                  lineHeight: 1.5,
                }}
              />
              {/* Suggestions dropdown */}
              {suggestionList.length > 0 && (
                <div
                  style={{
                    position: "absolute",
                    left: 0,
                    right: 0,
                    top: "100%",
                    zIndex: 10,
                    marginTop: 4,
                    border: "1px solid var(--line)",
                    background: "var(--panel)",
                    borderRadius: "var(--radius-card)",
                    boxShadow: "var(--shadow-lg)",
                    maxHeight: 240,
                    overflowY: "auto",
                  }}
                >
                  {suggestionList.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      onMouseDown={(e) => e.preventDefault()}
                      onClick={() => {
                        setQuestion(s.question_text);
                        setShowSuggestions(false);
                      }}
                      style={{
                        display: "block",
                        width: "100%",
                        padding: "8px 12px",
                        textAlign: "left",
                        background: "transparent",
                        border: "none",
                        borderBottom: "1px solid var(--line)",
                        cursor: "pointer",
                        fontSize: 13,
                        color: "var(--ink-2)",
                      }}
                    >
                      <div style={{ marginBottom: 2 }}>{s.question_text}</div>
                      {s.quick_answer_preview && (
                        <div
                          className="mono"
                          style={{ fontSize: 11, color: "var(--ink-4)" }}
                        >
                          {s.quick_answer_preview}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              <Btn
                variant="accent"
                onClick={handleAsk}
                disabled={streaming || question.trim().length < 5}
              >
                {streaming ? "Thinking\u2026" : "Ask"} <Icon.Arrow />
              </Btn>
              <div
                className="mono"
                style={{ fontSize: 10, color: "var(--ink-4)", textAlign: "center" }}
              >
                1 credit
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {state.status === "error" && state.errorMessage && (
          <div
            style={{
              marginBottom: 16,
              padding: "12px 14px",
              border: "1px solid var(--bad)",
              background: "var(--bad-bg)",
              borderRadius: "var(--radius)",
              fontSize: 13,
              color: "var(--bad)",
            }}
          >
            {state.errorMessage}
          </div>
        )}

        {/* Editorial answer — show mock when idle, live when streaming/done */}
        {(showMock || hasAnswer) && (
          <div style={{ position: "relative" }}>
            {/* Byline */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                marginBottom: 16,
                flexWrap: "wrap",
              }}
            >
              <div
                className="mono up"
                style={{ fontSize: 10.5, color: "var(--ink-4)" }}
              >
                BRIEF · {showMock ? fa.id.toUpperCase() : (state.questionId || "STREAMING").toUpperCase()}
              </div>
              <span
                style={{ width: 1, height: 10, background: "var(--line)" }}
              />
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Avatar initials={RP_DATA.user.initials} size={20} tone="signal" />
                <span style={{ fontSize: 12, color: "var(--ink-2)" }}>
                  {showMock ? fa.askedBy : (user?.full_name || "You")}
                </span>
                <span
                  className="mono"
                  style={{ fontSize: 10.5, color: "var(--ink-4)" }}
                >
                  · {showMock ? fa.askedAt : "Just now"}
                </span>
              </div>
              <div style={{ flex: 1 }} />
              {displayRisk && (
                <Pill tone={displayRisk === "high" ? "bad" : displayRisk === "med" ? "warn" : "ghost"}>
                  <Icon.Flag style={{ width: 10, height: 10 }} /> RISK{" "}
                  {displayRisk.toUpperCase()}
                </Pill>
              )}
              {displayConfidence !== null && displayConfidence !== undefined && (
                <ConfBadge score={displayConfidence} />
              )}
            </div>

            {/* Question headline */}
            <h2
              className="serif"
              style={{
                fontSize: 32,
                fontWeight: 400,
                lineHeight: 1.15,
                letterSpacing: "-0.015em",
                marginBottom: 18,
                color: "var(--ink)",
              }}
            >
              {displayQuestion}
            </h2>

            {/* Body */}
            <div className="rp-prose" style={{ maxWidth: 680 }}>
              {showMock ? (
                <>
                  <p className="dek">{fa.dek}</p>
                  {fa.body.map((chunk, i) =>
                    chunk.annot ? (
                      <AnnotSpan
                        key={i}
                        id={chunk.annotId || ""}
                        text={chunk.text}
                        annots={annotations}
                        setActive={setActiveAnnot}
                      />
                    ) : (
                      <span key={i}>{chunk.text}</span>
                    ),
                  )}
                </>
              ) : streaming ? (
                <p>
                  {state.answer}
                  <span
                    className="live-dot"
                    style={{ marginLeft: 6, verticalAlign: "middle" }}
                  />
                </p>
              ) : (
                <div className="prose-markdown">
                  <ReactMarkdown>{state.answer}</ReactMarkdown>
                </div>
              )}
            </div>

            {/* Recommended actions */}
            {displayActions.length > 0 && (
              <div style={{ marginTop: 32 }}>
                <div className="tick" style={{ marginBottom: 10 }}>
                  RECOMMENDED ACTIONS
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {displayActions.map((ac, i) => (
                    <div
                      key={i}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "56px 120px 1fr 70px auto",
                        gap: 12,
                        padding: "12px 14px",
                        border: "1px solid var(--line)",
                        background: "var(--bg)",
                        borderRadius: 3,
                        alignItems: "center",
                      }}
                    >
                      <Pill
                        tone={
                          ac.priority === "high"
                            ? "bad"
                            : ac.priority === "med"
                              ? "warn"
                              : "ghost"
                        }
                      >
                        {ac.priority.toUpperCase()}
                      </Pill>
                      <div
                        className="mono"
                        style={{
                          fontSize: 11,
                          color: "var(--ink-2)",
                          fontWeight: 600,
                        }}
                      >
                        {ac.team}
                      </div>
                      <div style={{ fontSize: 13, lineHeight: 1.4 }}>
                        {ac.action_text}
                      </div>
                      <div
                        className="mono tnum"
                        style={{ fontSize: 11, color: "var(--ink-3)" }}
                      >
                        {ac.due ? `Due ${ac.due}` : ""}
                      </div>
                      <Btn
                        size="sm"
                        variant="ghost"
                        onClick={() =>
                          toast.push({
                            tag: "ACTION",
                            text: `Assigned to ${ac.team}.`,
                          })
                        }
                      >
                        <Icon.Plus /> Task
                      </Btn>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Feedback bar — only after answer is done or showing mock */}
            {(showMock || state.status === "done") && (
              <div
                style={{
                  marginTop: 32,
                  padding: "14px 16px",
                  border: "1px solid var(--line)",
                  borderRadius: 3,
                  background: "var(--panel-2)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    flexWrap: "wrap",
                  }}
                >
                  <div
                    style={{
                      fontSize: 12.5,
                      color: "var(--ink-2)",
                      flex: "0 0 auto",
                    }}
                  >
                    <b>Was this brief accurate and useful?</b>
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Btn
                      variant={thumb === "up" ? "accent" : ""}
                      size="sm"
                      onClick={() => {
                        setThumb("up");
                        setShowFeedback(true);
                      }}
                    >
                      <Icon.Thumb /> Accurate
                    </Btn>
                    <Btn
                      variant={thumb === "down" ? "accent" : ""}
                      size="sm"
                      onClick={() => {
                        setThumb("down");
                        setShowFeedback(true);
                      }}
                    >
                      <Icon.ThumbDown /> Needs work
                    </Btn>
                  </div>
                  <div style={{ flex: 1 }} />
                  <Btn
                    variant={savedAsLearning ? "" : "primary"}
                    size="sm"
                    onClick={() => setShowLearningModal(true)}
                  >
                    <Icon.Spark />{" "}
                    {savedAsLearning ? "Saved as learning" : "Save as team learning"}
                  </Btn>
                  <Btn variant="ghost" size="sm">
                    <Icon.Bookmark /> Save
                  </Btn>
                  <Btn
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      toast.push({
                        tag: "EXPORT",
                        text: "PDF briefing queued for download.",
                      })
                    }
                  >
                    Export PDF
                  </Btn>
                </div>
                {showFeedback && (
                  <FeedbackForm
                    thumb={thumb}
                    onClose={() => setShowFeedback(false)}
                    onSubmit={() => {
                      setShowFeedback(false);
                      toast.push({
                        tag: "FEEDBACK",
                        text: "Thanks — routed to the RegPulse review queue.",
                      });
                    }}
                  />
                )}
              </div>
            )}

            {/* Credit info */}
            {state.status === "done" && state.creditBalance !== null && (
              <div
                className="mono"
                style={{
                  marginTop: 12,
                  fontSize: 11,
                  color: "var(--ink-4)",
                }}
              >
                Credits remaining: {state.creditBalance}
              </div>
            )}

            <BriefFooter />
          </div>
        )}
      </div>

      {/* ── Right rail — confidence, citations, debate ──────────────────── */}
      <aside
        style={{
          borderLeft: "1px solid var(--line)",
          background: "var(--panel)",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
        }}
      >
        {/* Confidence radial */}
        {displayConfidence !== null && displayConfidence !== undefined && (
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <div className="tick" style={{ marginBottom: 8 }}>
              CONFIDENCE
            </div>
            <ConfidenceRadial score={displayConfidence} />
            <div
              style={{
                marginTop: 10,
                fontSize: 11.5,
                color: "var(--ink-3)",
                lineHeight: 1.4,
              }}
            >
              {displayConfidence >= 0.7
                ? "High-precision citations, no cross-jurisdiction conflicts, supporting chunks from the canonical circular."
                : displayConfidence >= 0.5
                  ? "Moderate confidence — some citations may need manual verification."
                  : "Low confidence — consider consulting a regulatory expert."}
            </div>
          </div>
        )}

        {/* Citations */}
        {displayCitations.length > 0 && (
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <div className="tick" style={{ marginBottom: 10 }}>
              CITATIONS · {displayCitations.length}
            </div>
            {displayCitations.map((c, i) => (
              <div
                key={i}
                onClick={() => setSelectedCitation(i)}
                style={{
                  padding: "10px 12px",
                  marginBottom: 6,
                  cursor: "pointer",
                  borderRadius: 2,
                  border: `1px solid ${selectedCitation === i ? "var(--signal)" : "var(--line)"}`,
                  background:
                    selectedCitation === i ? "var(--signal-bg)" : "var(--bg)",
                  transition: "border-color .12s, background .12s",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 4,
                  }}
                >
                  <span
                    className="mono"
                    style={{ fontSize: 10, fontWeight: 600, color: "var(--signal)" }}
                  >
                    [{i + 1}]
                  </span>
                  <span
                    className="mono"
                    style={{ fontSize: 10.5, color: "var(--ink-3)" }}
                  >
                    {c.section_reference}
                  </span>
                </div>
                <div
                  className="serif"
                  style={{
                    fontSize: 12.5,
                    fontStyle: "italic",
                    color: "var(--ink-2)",
                    lineHeight: 1.45,
                  }}
                >
                  &ldquo;{c.verbatim_quote}&rdquo;
                </div>
                <div
                  className="mono"
                  style={{
                    fontSize: 10,
                    color: "var(--ink-4)",
                    marginTop: 6,
                  }}
                >
                  {c.circular_number}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Debate thread */}
        {displayDebate.length > 0 && (
          <div
            style={{
              padding: "14px 16px",
              borderBottom: "1px solid var(--line)",
            }}
          >
            <div className="tick" style={{ marginBottom: 10 }}>
              DEBATE · {displayDebate.length}
            </div>
            {displayDebate.map((d, i) => (
              <div
                key={i}
                style={{
                  padding: "10px 0",
                  borderBottom:
                    i === displayDebate.length - 1
                      ? "none"
                      : "1px solid var(--line)",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 4,
                  }}
                >
                  <Avatar
                    initials={d.who}
                    size={18}
                    tone={d.who === "PM" ? "signal" : "default"}
                  />
                  <span style={{ fontSize: 11.5, fontWeight: 600 }}>
                    {d.who}
                  </span>
                  <span
                    className="mono"
                    style={{ fontSize: 10, color: "var(--ink-4)" }}
                  >
                    {d.role}
                  </span>
                  <span style={{ flex: 1 }} />
                  <span
                    className="mono"
                    style={{ fontSize: 10, color: "var(--ink-4)" }}
                  >
                    {d.when}
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--ink-2)",
                    lineHeight: 1.45,
                  }}
                >
                  {d.text}
                </div>
              </div>
            ))}
            <div style={{ marginTop: 10, display: "flex", gap: 6 }}>
              <input
                className="input"
                placeholder="Add to debate\u2026"
                style={{ fontSize: 12 }}
              />
              <Btn size="sm" variant="primary">
                Post
              </Btn>
            </div>
          </div>
        )}

        {/* Annotations hint */}
        <div
          style={{
            padding: "14px 16px",
            background: "var(--bg-1)",
            marginTop: "auto",
          }}
        >
          <div className="tick" style={{ marginBottom: 8 }}>
            ANNOTATIONS · {annotations.length}
          </div>
          <div
            style={{
              fontSize: 11.5,
              color: "var(--ink-3)",
              lineHeight: 1.5,
            }}
          >
            Select any passage in the brief to annotate. Margin notes are
            visible only to your team.
          </div>
        </div>
      </aside>

      {/* ── Modals ─────────────────────────────────────────────────────── */}
      {showLearningModal && (
        <LearningModal
          question={displayQuestion}
          note={learningNote}
          setNote={setLearningNote}
          onSave={saveLearning}
          onClose={() => setShowLearningModal(false)}
        />
      )}
      {activeAnnot && (
        <AnnotPopover
          annot={annotations.find((x) => x.id === activeAnnot) || null}
          onClose={() => setActiveAnnot(null)}
        />
      )}
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────────────────────── */

function AnnotSpan({
  id,
  text,
  annots,
  setActive,
}: {
  id: string;
  text: string;
  annots: Annotation[];
  setActive: (id: string) => void;
}) {
  const has = annots.some((a) => a.id === id);
  return (
    <mark className="annot" onClick={() => setActive(id)} style={{ position: "relative" }}>
      {text}
      {has && (
        <sup
          className="mono"
          style={{
            marginLeft: 2,
            fontSize: 9,
            color: "var(--signal)",
            fontWeight: 700,
          }}
        >
          §
        </sup>
      )}
    </mark>
  );
}

function AnnotPopover({
  annot,
  onClose,
}: {
  annot: Annotation | null;
  onClose: () => void;
}) {
  if (!annot) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 80,
        background: "rgba(0,0,0,0.2)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          top: "30%",
          left: "35%",
          width: 360,
          background: "var(--panel)",
          border: "1px solid var(--line-2)",
          boxShadow: "var(--shadow-lg)",
          borderRadius: 4,
          padding: 16,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 8,
          }}
        >
          <Avatar initials={annot.by} size={22} tone="signal" />
          <div>
            <div style={{ fontSize: 12.5, fontWeight: 600 }}>{annot.by}</div>
            <div
              className="mono"
              style={{ fontSize: 10, color: "var(--ink-4)" }}
            >
              {annot.when} ago · on &ldquo;{annot.text}&rdquo;
            </div>
          </div>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" icon onClick={onClose}>
            <Icon.Close />
          </Btn>
        </div>
        <div
          className="serif"
          style={{
            fontSize: 14,
            fontStyle: "italic",
            lineHeight: 1.5,
            color: "var(--ink-2)",
            borderLeft: "2px solid var(--signal)",
            paddingLeft: 10,
          }}
        >
          {annot.note}
        </div>
        <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
          <Btn size="sm">
            <Icon.Plus /> Reply
          </Btn>
          <Btn variant="ghost" size="sm">
            Resolve
          </Btn>
        </div>
      </div>
    </div>
  );
}

function ConfBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: 11,
        color: "var(--ink-3)",
      }}
    >
      <span className="mono up">CONF</span>
      <span
        className="mono tnum"
        style={{ fontWeight: 600, color: "var(--ink)" }}
      >
        {pct}%
      </span>
      <div style={{ width: 40 }}>
        <div className="bar good">
          <span style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}

function ConfidenceRadial({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const r = 32;
  const c = 2 * Math.PI * r;
  const off = c - (c * pct) / 100;
  const label =
    pct >= 70 ? "HIGH CONFIDENCE" : pct >= 50 ? "MODERATE" : "LOW CONFIDENCE";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <svg
        width="84"
        height="84"
        viewBox="0 0 84 84"
        style={{ transform: "rotate(-90deg)" }}
      >
        <circle
          cx="42"
          cy="42"
          r={r}
          stroke="var(--line)"
          strokeWidth="6"
          fill="none"
        />
        <circle
          cx="42"
          cy="42"
          r={r}
          stroke="var(--signal)"
          strokeWidth="6"
          fill="none"
          strokeLinecap="butt"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
      </svg>
      <div>
        <div
          className="tnum"
          style={{
            fontSize: 28,
            fontWeight: 600,
            letterSpacing: "-0.02em",
            lineHeight: 1,
          }}
        >
          {pct}
          <span style={{ fontSize: 14, color: "var(--ink-4)" }}>%</span>
        </div>
        <div
          className="mono up"
          style={{ fontSize: 10, color: "var(--ink-4)", marginTop: 4 }}
        >
          {label}
        </div>
      </div>
    </div>
  );
}

function FeedbackForm({
  thumb,
  onClose,
  onSubmit,
}: {
  thumb: "up" | "down" | null;
  onClose: () => void;
  onSubmit: () => void;
}) {
  const options =
    thumb === "down"
      ? [
          "Missing a relevant circular",
          "Misinterpreted a citation",
          "Risk level too low",
          "Risk level too high",
          "Actions not aligned with our structure",
          "Stale — superseded circular cited",
        ]
      : [
          "Exactly what I needed",
          "Cited the right sections",
          "Actions are actionable",
          "Confidence feels right",
        ];
  const [checked, setChecked] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const toggle = (o: string) =>
    setChecked((c) =>
      c.includes(o) ? c.filter((x) => x !== o) : [...c, o],
    );
  return (
    <div
      style={{
        marginTop: 12,
        paddingTop: 12,
        borderTop: "1px solid var(--line)",
      }}
    >
      <div
        style={{ fontSize: 11.5, color: "var(--ink-3)", marginBottom: 8 }}
      >
        {thumb === "down" ? "What\u2019s wrong or missing?" : "What worked well?"}
      </div>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 5,
          marginBottom: 10,
        }}
      >
        {options.map((o) => (
          <label
            key={o}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 8px",
              fontSize: 11.5,
              border: `1px solid ${checked.includes(o) ? "var(--signal)" : "var(--line)"}`,
              background: checked.includes(o)
                ? "var(--signal-bg)"
                : "var(--bg)",
              borderRadius: 2,
              cursor: "pointer",
              color: checked.includes(o)
                ? "var(--signal-ink)"
                : "var(--ink-2)",
            }}
          >
            <input
              type="checkbox"
              checked={checked.includes(o)}
              onChange={() => toggle(o)}
              className="checkbox"
            />
            {o}
          </label>
        ))}
      </div>
      <textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="input"
        placeholder="Optional: what should the brief have said?"
        style={{ minHeight: 60, fontSize: 12.5 }}
      />
      <div
        style={{
          display: "flex",
          gap: 6,
          marginTop: 8,
          justifyContent: "flex-end",
        }}
      >
        <Btn variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Btn>
        <Btn variant="primary" size="sm" onClick={onSubmit}>
          Send to review queue
        </Btn>
      </div>
    </div>
  );
}

function LearningModal({
  question,
  note,
  setNote,
  onSave,
  onClose,
}: {
  question: string;
  note: string;
  setNote: (n: string) => void;
  onSave: () => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(
    "Tier-1 floor for UL NBFCs is 10%, not 9.5% — glide-path ends Q4 FY27.",
  );
  const [tags] = useState(["SBR", "Tier-1", "FY27"]);
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 90,
        background: "rgba(0,0,0,0.35)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 560,
          background: "var(--panel)",
          border: "1px solid var(--line-2)",
          boxShadow: "var(--shadow-lg)",
          borderRadius: 4,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            padding: "14px 18px",
            borderBottom: "1px solid var(--line)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <Icon.Spark style={{ color: "var(--signal)" }} />
          <h3 style={{ fontSize: 14, fontWeight: 600 }}>
            Save as team learning
          </h3>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" icon onClick={onClose}>
            <Icon.Close />
          </Btn>
        </div>
        <div style={{ padding: 18 }}>
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--ink-4)",
              marginBottom: 4,
              letterSpacing: ".08em",
            }}
          >
            SOURCE QUESTION
          </div>
          <div
            className="serif"
            style={{
              fontSize: 14,
              fontStyle: "italic",
              color: "var(--ink-2)",
              marginBottom: 16,
              lineHeight: 1.4,
            }}
          >
            &ldquo;{question}&rdquo;
          </div>
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--ink-4)",
              marginBottom: 4,
              letterSpacing: ".08em",
            }}
          >
            LEARNING · ONE-LINE TAKEAWAY
          </div>
          <input
            className="input"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ marginBottom: 12 }}
          />
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--ink-4)",
              marginBottom: 4,
              letterSpacing: ".08em",
            }}
          >
            NOTES (OPTIONAL)
          </div>
          <textarea
            className="input"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Context for the team — why this matters, what changed."
            style={{ minHeight: 72, marginBottom: 12 }}
          />
          <div
            className="mono"
            style={{
              fontSize: 10,
              color: "var(--ink-4)",
              marginBottom: 6,
              letterSpacing: ".08em",
            }}
          >
            TAGS
          </div>
          <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
            {tags.map((t) => (
              <Pill key={t} tone="amber">
                {t}{" "}
                <Icon.Close style={{ width: 9, height: 9, marginLeft: 4 }} />
              </Pill>
            ))}
            <Pill tone="ghost">+ add</Pill>
          </div>
        </div>
        <div
          style={{
            padding: "12px 18px",
            background: "var(--bg-1)",
            borderTop: "1px solid var(--line)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <label
            style={{
              fontSize: 12,
              color: "var(--ink-3)",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <input type="checkbox" className="checkbox" defaultChecked />{" "}
            Notify team (5 members)
          </label>
          <div style={{ flex: 1 }} />
          <Btn variant="ghost" onClick={onClose}>
            Cancel
          </Btn>
          <Btn variant="accent" onClick={onSave}>
            <Icon.Spark /> Save learning
          </Btn>
        </div>
      </div>
    </div>
  );
}

function BriefFooter() {
  return (
    <div
      style={{
        marginTop: 32,
        padding: "16px 0",
        borderTop: "1px solid var(--line)",
        fontSize: 11,
        color: "var(--ink-4)",
        lineHeight: 1.6,
      }}
    >
      <div className="mono up" style={{ marginBottom: 4 }}>
        DISCLAIMER
      </div>
      RegPulse is not a legal advisory service. Briefs are AI-generated from
      indexed RBI circulars and must be verified at rbi.org.in before action.
    </div>
  );
}
