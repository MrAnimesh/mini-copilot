import type { AgentEvent } from "../lib/sse";
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
  events: AgentEvent[];
}) {
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
            padding: "6px 10px",
            background: "#11161d",
            borderRadius: 4,
          }}
        >
          <div style={{ fontSize: 12, opacity: 0.7 }}>
            step {ev.step} • {ev.type}
          </div>

          {ev.type === "token" ? (
            <span>{String(ev.data.text ?? "")}</span>
          ) : ev.type === "approval_required" ? (
            <ApprovalRow ev={ev} />
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

function ApprovalRow({ ev }: { ev: AgentEvent }) {
  const approvalId = String(ev.data.approval_id);

  return (
    <div>
      <pre
        style={{
          margin: 0,
          whiteSpace: "pre-wrap",
          fontSize: 12,
        }}
      >
        {JSON.stringify(ev.data, null, 2)}
      </pre>

      <div
        style={{
          display: "flex",
          gap: 8,
          marginTop: 6,
        }}
      >
        <button onClick={() => approve(approvalId, true)}>
          Approve
        </button>

        <button onClick={() => approve(approvalId, false)}>
          Reject
        </button>
      </div>
    </div>
  );
}