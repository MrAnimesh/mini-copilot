import type { AgentEvent } from "../lib/sse.ts";
import { approve } from "../lib/sse";

const colors: Record<string, string> = {
  token: "#9ca3af",
  tool_call: "#60a5fa",
  tool_result: "#34d399",
  approval_required: "#fbbf24",
  done: "#a78bfa",
  error: "#f87171",
};

export function Timeline({
  events,
}: {
  events: AgentEvent[]
}) {
  const answered = new Set<string>();
  for (const ev of events) {
    if (ev.type === "tool_result") {
      const aid = (ev.data as { approval_id?: string }).approval_id;
      if (aid) answered.add(aid);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
      {events.map((ev, i) => (
        <div
          key={i}
          style={{
            borderLeft: `3px solid ${colors[ev.type] ?? "#555"}`,
            padding: "8px 12px",
            background: ev.type === "approval_required" ? "#3b2f12" : "#11161d",
            borderRadius: 4,
          }}
        >
          <div style={{ fontSize: 12, opacity: 0.7, marginBottom: 4 }}>
            step {ev.step} • {ev.type}
          </div>

          {ev.type === "token" ? (
            <span>{String((ev.data as { text?: string }).text ?? "")}</span>
          ) : ev.type === "approval_required" ? (
            <ApprovalRow ev={ev} answered={answered} />
          ) : (
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                fontSize: 12,
              }}
            >
              {JSON.stringify(ev.data, null, 2)}
            </pre>
          )}
        </div>
      ))}
    </div>
  );
}

function ApprovalRow({ ev, answered }: { ev: AgentEvent; answered: Set<string> }) {
  const data = typeof ev.data === "string" ?
    (JSON.parse(ev.data) as Record<string, unknown>) : (ev.data as Record<string, unknown>);
  const approvalId = String(ev.data.approval_id);
  const tool = String(data.tool ?? "?");
  const permission = String(data.permission ?? "?");
  const isAnswered = approvalId && answered.has(approvalId);

  return (
    <div>
      <div style={{ fontWeight: 600, marginBottom: 6 }}>
        Approval required: <code>{tool}</code>{" "}
        <span style={{ opacity: 0.7 }}>({permission})</span>
      </div>
      <pre
        style={{
          margin: "0 0 8px 0",
          whiteSpace: "pre-wrap",
          fontSize: 12,
          background: "#11161d",
          padding: 8,
          borderRadius: 4,
          maxHeight: 240,
          overflow: "auto"
        }}
      >
        {JSON.stringify(data.arguments ?? {}, null, 2)}
      </pre>
      {isAnswered ? (
        <div style={{ opacity: 0.7, fontStyle: "italic" }}>resolved</div>
      ) : (

        <div
          style={{
            display: "flex",
            gap: 8,
          }}
        >
          <button onClick={() => approve(approvalId, true)}
            style={btnStyle("#16a34a")}>
            Approve
          </button>

          <button onClick={() => approve(approvalId, false)}
            style={btnStyle("#dc2626")}>
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    background: bg,
    color: "white",
    border: "none",
    borderRadius: 4,
    padding: "8px 16px",
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer"
  }
}
