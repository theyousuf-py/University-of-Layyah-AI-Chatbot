import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";

const API = process.env.REACT_APP_API_URL || "http://localhost:8000";

const SUGGESTED = [
  "What are the admission requirements?",
  "Show me the fee structure",
  "List of departments",
  "Are hostel facilities available?",
  "When will the semester start?",
];

/* ── UL Logo SVG ─────────────────────────────────────────────────────────────── */
const ULLogo = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none">
    <circle cx="24" cy="24" r="24" fill="white"/>
    <text x="50%" y="54%" dominantBaseline="middle" textAnchor="middle"
      fill="#1a6b2a" fontSize="16" fontWeight="800" fontFamily="Inter,sans-serif">UL</text>
  </svg>
);

/* ── Chat Icon ───────────────────────────────────────────────────────────────── */
const ChatIcon = ({ size = 26 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
  </svg>
);

/* ── Close Icon ──────────────────────────────────────────────────────────────── */
const CloseIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);

/* ── Send Icon ───────────────────────────────────────────────────────────────── */
const SendIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="white">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
);

/* ── Typing Dots ─────────────────────────────────────────────────────────────── */
const TypingDots = () => (
  <div style={{ display: "flex", gap: 4, alignItems: "center", padding: "3px 0" }}>
    {[1,2,3].map(i => (
      <div key={i} className={`dot-${i}`} style={{
        width: 7, height: 7, borderRadius: "50%",
        background: "var(--ul-green-light)",
      }}/>
    ))}
  </div>
);

/* ── Message Bubble ──────────────────────────────────────────────────────────── */
const MessageBubble = ({ msg, isLast }) => {
  const isBot  = msg.role === "bot";
  const isLoad = msg.loading;

  return (
    <div className={isLast ? "msg-appear" : ""} style={{
      display: "flex",
      flexDirection: isBot ? "row" : "row-reverse",
      alignItems: "flex-end",
      gap: 8,
      marginBottom: 14,
    }}>
      {/* Bot avatar */}
      {isBot && (
        <div style={{
          width: 28, height: 28, borderRadius: "50%", flexShrink: 0,
          background: "var(--ul-green)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 9, fontWeight: 700, color: "white",
          border: "2px solid var(--ul-green-pale)",
        }}>
          UL
        </div>
      )}

      {/* Bubble */}
      <div style={{
        maxWidth: "78%",
        background: isBot ? "var(--white)" : "var(--ul-green)",
        color: isBot ? "var(--gray-700)" : "white",
        borderRadius: isBot ? "4px 14px 14px 14px" : "14px 4px 14px 14px",
        padding: "10px 14px",
        fontSize: 13.5,
        lineHeight: 1.7,
        boxShadow: isBot
          ? "0 1px 4px rgba(0,0,0,0.08)"
          : "0 2px 8px rgba(26,107,42,0.3)",
        border: isBot ? "1px solid var(--gray-200)" : "none",
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
      }}>
        {isLoad ? <TypingDots /> : msg.text}
      </div>

      {/* Cache badge */}
      {isBot && msg.cacheHit && !isLoad && (
        <div style={{
          fontSize: 9, color: "var(--ul-green)",
          background: "var(--ul-green-pale)",
          borderRadius: 99, padding: "2px 6px",
          alignSelf: "flex-end", marginBottom: 2,
          border: "1px solid rgba(26,107,42,0.2)",
          whiteSpace: "nowrap",
        }}>
          ⚡ cached
        </div>
      )}
    </div>
  );
};

/* ── Welcome Screen ──────────────────────────────────────────────────────────── */
const WelcomeScreen = ({ onSelect }) => (
  <div style={{ padding: "8px 4px" }}>
    <div style={{
      background: "linear-gradient(135deg, var(--ul-green) 0%, var(--ul-green-light) 100%)",
      borderRadius: 12, padding: "16px",
      marginBottom: 16, color: "white",
    }}>
      <div style={{ fontSize: 22, marginBottom: 6 }}>👋</div>
      <p style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>Assalam o Alaikum!</p>
      <p style={{ fontSize: 12.5, opacity: 0.9, lineHeight: 1.6 }}>
        I'm UniBot — University of Layyah's AI assistant. Ask me anything about admissions, fees, or departments!
      </p>
    </div>

    <p style={{ fontSize: 11, fontWeight: 600, color: "var(--gray-400)", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.08em" }}>
      Quick Questions
    </p>
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      {SUGGESTED.map((q, i) => (
        <button key={i} onClick={() => onSelect(q)} style={{
          background: "var(--white)",
          border: "1px solid var(--gray-200)",
          borderRadius: 9, padding: "9px 12px",
          fontSize: 12.5, color: "var(--gray-700)",
          textAlign: "left", transition: "all 0.15s",
          display: "flex", alignItems: "center", gap: 8,
        }}
        onMouseEnter={e => {
          e.currentTarget.style.borderColor = "var(--ul-green)";
          e.currentTarget.style.color = "var(--ul-green)";
          e.currentTarget.style.background = "var(--ul-green-pale)";
        }}
        onMouseLeave={e => {
          e.currentTarget.style.borderColor = "var(--gray-200)";
          e.currentTarget.style.color = "var(--gray-700)";
          e.currentTarget.style.background = "var(--white)";
        }}>
          <span style={{ color: "var(--ul-green)", fontSize: 11 }}>▶</span>
          {q}
        </button>
      ))}
    </div>
  </div>
);

/* ── Chat Panel ──────────────────────────────────────────────────────────────── */
const ChatPanel = ({ onClose }) => {
  const [messages,  setMessages]  = useState([]);
  const [input,     setInput]     = useState("");
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);

  // ── NEW: Conversation history (last 5 Q&A pairs) ──────────────────────────
  // Stores {role, content} objects — grows with each exchange
  const [history, setHistory] = useState([]);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);
  const msgId     = useRef(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    setTimeout(() => inputRef.current?.focus(), 300);
  }, []);

  const sendMessage = useCallback(async (text) => {
    const q = (text || input).trim();
    if (!q || loading) return;

    setInput("");
    setError(null);
    const ta = inputRef.current;
    if (ta) ta.style.height = "auto";

    const userMsg = { id: msgId.current++, role: "user", text: q };
    const loadId  = msgId.current++;
    setMessages(prev => [...prev, userMsg, { id: loadId, role: "bot", loading: true }]);
    setLoading(true);

    try {
      // ── Send question + conversation history to backend ────────────────────
      const res  = await axios.post(`${API}/api/chat`, {
        question: q,
        history:  history,   // ← send last N Q&A pairs
      });
      const data = res.data;
      const answer = data.answer;

      setMessages(prev => prev.map(m =>
        m.id === loadId
          ? { id: loadId, role: "bot", text: answer, cacheHit: data.cache_hit }
          : m
      ));

      // ── Update history with this exchange ─────────────────────────────────
      setHistory(prev => [
        ...prev,
        { role: "user",      content: q      },
        { role: "assistant", content: answer },
      ]);

    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== loadId));
      const detail = err.response?.data?.detail;
      setError(err.response?.status === 429
        ? "Too many requests. Please wait a moment."
        : (detail || "Server se connect nahi ho pa raha. Retry karein.")
      );
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [input, loading, history]);

  const handleKey = e => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };
  const handleChange = e => {
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 90) + "px";
    setInput(e.target.value);
  };

  const canSend = input.trim() && !loading;
  const isEmpty = messages.length === 0;

  return (
    <div style={{
      position: "absolute",
      bottom: 0, right: 0,
      width: 360,
      height: 540,
      background: "var(--gray-50)",
      borderRadius: 20,
      boxShadow: "var(--shadow-panel)",
      display: "flex",
      flexDirection: "column",
      overflow: "hidden",
      animation: "slideUp 0.3s cubic-bezier(.22,1,.36,1) forwards",
      border: "1px solid rgba(26,107,42,0.15)",
    }}>

      {/* ── Header ── */}
      <div style={{
        background: "linear-gradient(135deg, var(--ul-green-dark) 0%, var(--ul-green) 100%)",
        padding: "14px 16px",
        display: "flex", alignItems: "center", gap: 10,
        flexShrink: 0,
      }}>
        <div style={{
          width: 38, height: 38, borderRadius: "50%",
          background: "rgba(255,255,255,0.15)",
          border: "2px solid rgba(255,255,255,0.3)",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 11, fontWeight: 800, color: "white", flexShrink: 0,
        }}>
          UL
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 14, color: "white" }}>UL Assistant</div>
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 2 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#4ade80" }} />
            <span style={{ fontSize: 11, color: "rgba(255,255,255,0.8)" }}>University of Layyah</span>
          </div>
        </div>
        <button onClick={onClose} style={{
          background: "rgba(255,255,255,0.15)",
          border: "none", borderRadius: "50%",
          width: 32, height: 32,
          display: "flex", alignItems: "center", justifyContent: "center",
          transition: "background 0.15s",
        }}
        onMouseEnter={e => e.currentTarget.style.background = "rgba(255,255,255,0.25)"}
        onMouseLeave={e => e.currentTarget.style.background = "rgba(255,255,255,0.15)"}
        >
          <CloseIcon />
        </button>
      </div>

      {/* ── Messages Area ── */}
      <div style={{
        flex: 1, overflowY: "auto",
        padding: "16px 14px 8px",
        display: "flex", flexDirection: "column",
      }}>
        {isEmpty
          ? <WelcomeScreen onSelect={q => sendMessage(q)} />
          : messages.map((msg, i) => (
              <MessageBubble key={msg.id} msg={msg} isLast={i === messages.length - 1} />
            ))
        }

        {error && (
          <div style={{
            background: "#fef2f2", border: "1px solid #fecaca",
            borderRadius: 9, padding: "8px 12px",
            color: "#dc2626", fontSize: 12,
            display: "flex", gap: 6, alignItems: "center",
            marginBottom: 10,
          }}>
            <span>⚠️</span>
            <span style={{ flex: 1 }}>{error}</span>
            <button onClick={() => setError(null)} style={{ background: "none", border: "none", color: "inherit", opacity: 0.6, fontSize: 14, lineHeight: 1 }}>×</button>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input Area ── */}
      <div style={{
        background: "var(--white)",
        borderTop: "1px solid var(--gray-200)",
        padding: "10px 12px 12px",
        flexShrink: 0,
      }}>
        <div style={{
          display: "flex", gap: 8, alignItems: "flex-end",
          background: "var(--gray-50)",
          border: `1.5px solid ${input ? "var(--ul-green)" : "var(--gray-200)"}`,
          borderRadius: 12, padding: "8px 8px 8px 12px",
          transition: "border-color 0.2s",
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleChange}
            onKeyDown={handleKey}
            disabled={loading}
            placeholder="Ask anything about the university…"
            rows={1}
            style={{
              flex: 1, background: "transparent", border: "none",
              color: "var(--gray-700)", fontSize: 13, lineHeight: 1.5,
              fontFamily: "inherit", resize: "none",
              minHeight: 22, maxHeight: 90,
              caretColor: "var(--ul-green)",
            }}
          />
          <button onClick={() => sendMessage()} disabled={!canSend} style={{
            width: 34, height: 34, borderRadius: 9, flexShrink: 0,
            background: canSend ? "var(--ul-green)" : "var(--gray-200)",
            border: "none",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.15s",
            boxShadow: canSend ? "0 2px 8px rgba(26,107,42,0.35)" : "none",
          }}
          onMouseEnter={e => { if (canSend) e.currentTarget.style.background = "var(--ul-green-dark)"; }}
          onMouseLeave={e => { if (canSend) e.currentTarget.style.background = "var(--ul-green)"; }}
          >
            {loading
              ? <div style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid rgba(255,255,255,0.4)", borderTopColor: "white", animation: "spin 0.7s linear infinite" }} />
              : <SendIcon />
            }
          </button>
        </div>

        <p style={{ textAlign: "center", marginTop: 7, fontSize: 10, color: "var(--gray-400)" }}>
          University of Layyah · ul.edu.pk
        </p>
      </div>
    </div>
  );
};

/* ── Floating Toggle Button ──────────────────────────────────────────────────── */
const FloatingButton = ({ isOpen, onClick, unreadCount }) => (
  <button onClick={onClick} style={{
    width: 56, height: 56, borderRadius: "50%",
    background: isOpen
      ? "linear-gradient(135deg, #145220, #1a6b2a)"
      : "linear-gradient(135deg, #1a6b2a, #218a35)",
    border: "none",
    display: "flex", alignItems: "center", justifyContent: "center",
    boxShadow: isOpen
      ? "0 4px 16px rgba(26,107,42,0.5)"
      : "0 4px 20px rgba(26,107,42,0.5), 0 0 0 0 rgba(26,107,42,0.4)",
    cursor: "pointer",
    transition: "all 0.25s cubic-bezier(.22,1,.36,1)",
    position: "relative",
    animation: isOpen ? "none" : "glow 2.5s infinite",
  }}
  onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.08)"; }}
  onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; }}
  >
    {isOpen ? <CloseIcon /> : <ChatIcon />}

    {!isOpen && unreadCount > 0 && (
      <div style={{
        position: "absolute", top: -2, right: -2,
        width: 18, height: 18, borderRadius: "50%",
        background: "var(--ul-orange)",
        border: "2px solid white",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 9, fontWeight: 700, color: "white",
        animation: "pulse-badge 1.5s infinite",
      }}>
        {unreadCount}
      </div>
    )}
  </button>
);

/* ── Tooltip ─────────────────────────────────────────────────────────────────── */
const Tooltip = ({ visible }) => (
  <div style={{
    position: "absolute",
    bottom: "100%", right: 0,
    marginBottom: 10,
    background: "var(--ul-green-dark)",
    color: "white",
    borderRadius: 9, padding: "8px 12px",
    fontSize: 12, fontWeight: 500,
    whiteSpace: "nowrap",
    boxShadow: "0 4px 16px rgba(0,0,0,0.15)",
    opacity: visible ? 1 : 0,
    transform: visible ? "translateY(0)" : "translateY(4px)",
    transition: "all 0.2s",
    pointerEvents: "none",
  }}>
    💬 Ask UniBot!
    <div style={{
      position: "absolute", bottom: -5, right: 20,
      width: 10, height: 10,
      background: "var(--ul-green-dark)",
      transform: "rotate(45deg)",
    }} />
  </div>
);

/* ── Main App ────────────────────────────────────────────────────────────────── */
export default function App() {
  const [isOpen,      setIsOpen]      = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);
  const [unread,      setUnread]      = useState(1);

  useEffect(() => {
    const t1 = setTimeout(() => setShowTooltip(true),  1500);
    const t2 = setTimeout(() => setShowTooltip(false), 5500);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const handleOpen = () => {
    setIsOpen(prev => !prev);
    setUnread(0);
    setShowTooltip(false);
  };

  return (
    <div style={{
      position: "fixed",
      bottom: 90,
      right: 20,
      zIndex: 99999,
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-end",
      gap: 12,
    }}>
      {isOpen && (
        <div style={{ position: "relative" }}>
          <ChatPanel onClose={() => setIsOpen(false)} />
        </div>
      )}

      <div style={{ position: "relative" }}>
        <Tooltip visible={showTooltip && !isOpen} />
        <FloatingButton isOpen={isOpen} onClick={handleOpen} unreadCount={unread} />
      </div>
    </div>
  );
}
