console.log("APP.tsx loaded v3");


import React, { useState, useMemo } from "react";

import { Timeline } from "./components/Timeline";

import {
    approve,
  streamAgent,
  type AgentEvent,
} from "./lib/sse";


export default function App() {
  const [workspace, setWorkspace] = useState("");

  const [task, setTask] = useState("");

  const [mode, setMode] = useState<
    "manual" | "auto-edit" | "yolo"
  >("manual");

  const [events, setEvents] = useState<AgentEvent[]>([]);

  const [running, setRunning] = useState(false);

  // Pending approvals = approval_required events whose approval_id has not
// appeared in any tool result yet.
const pendingApprovals = useMemo(() => {
  const answered = new Set<string>();

  for (const ev of events) {
    if (ev.type === "tool_result") {
      const aid = (ev.data as { approval_id?: string }).approval_id;

      if (aid) {
        answered.add(aid);
      }
    }
  }

  return events.filter(
    (ev) =>
      ev.type === "approval_required" &&
      !answered.has(
        String((ev.data as { approval_id?: string }).approval_id)
      )
  );
}, [events]);


  async function run() {
    setEvents([]);

    setRunning(true);

    try {
      for await (const ev of streamAgent(
        "http://localhost:8765/agent/run",
        {
          workspace,
          task,
          mode,
        }
      )) {
        console.log("[agent event]", ev.type, ev);
        
        setEvents((prev) => [...prev, ev]);

        if (
          ev.type === "done" ||
          ev.type === "error"
        ) {
          break;
        }
      }

    } catch (e) {
      setEvents((prev) => [
        ...prev,
        {
          type: "error",
          step: 0,
          data: {
            error: String(e),
          },
        },
      ]);

    } finally {
      setRunning(false);
    }
  }


  return (
    <div
      style={{
        maxWidth: 900,
        margin: "0 auto",
        padding: 24,
      }}
    >
      <h1 style={{ marginTop: 0 }}>
        mini-copilot | new build
      </h1>

      <p style={{ opacity: 0.7 }}>
        Offline agentic coding • powered by local Ollama
      </p>
      {pendingApprovals.length > 0 &&(
        <ApprovalBanner events={pendingApprovals}/>
      )}

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          marginBottom: 16,
        }}
      >
        <input
          placeholder="Workspace folder (absolute path)"
          value={workspace}
          onChange={(e) =>
            setWorkspace(e.target.value)
          }
          style={inputStyle}
        />

        <textarea
          placeholder="Describe the task..."
          value={task}
          onChange={(e) =>
            setTask(e.target.value)
          }
          rows={4}
          style={inputStyle}
        />

        <div
          style={{
            display: "flex",
            gap: 8,
            alignItems: "center",
          }}
        >
          <label>Mode:</label>

          <select
            value={mode}
            onChange={(e) =>
              setMode(
                e.target.value as never
              )
            }
            style={inputStyle}
          >
            <option value="manual">
              manual (approve every write/exec)
            </option>

            <option value="auto-edit">
              auto-edit (auto-approve writes)
            </option>

            <option value="yolo">
              yolo (no approvals)
            </option>
          </select>

          <button
            onClick={run}
            disabled={
              running ||
              !workspace ||
              !task
            }
          >
            {running
              ? "Running..."
              : "Run agent"}
          </button>
        </div>
      </div>

      <Timeline events={events} />
    </div>
  );
}

function ApprovalBanner({ events }: { events: AgentEvent[] }) {
  return (
    <div
      style={{
        position: "sticky",
        top: 0,
        zIndex: 10,
        background: "#3b2f12",
        border: "2px solid #fbbf24",
        borderRadius: 6,
        padding: 16,
        marginBottom: 16,
      }}
    >
      <div
        style={{
          fontWeight: 700,
          color: "#fbbf24",
          marginBottom: 8,
        }}
      >
        {events.length} pending approval
        {events.length > 1 ? "s" : ""}
      </div>

      {events.map((ev, i) => {
        const data = ev.data as {
          approval_id?: string;
          tool?: string;
          permission?: string;
          arguments?: unknown;
        };

        const aid = String(data.approval_id ?? "");

        return (
  <div
    key={i}
    style={{
      borderTop: i > 0 ? "1px solid #5a4a1f" : undefined,
      paddingTop: i > 0 ? 12 : 0,
      marginTop: i > 0 ? 12 : 0,
    }}
  >
    <div style={{ marginBottom: 6 }}>
      Tool: <code>{data.tool}</code>{" "}
      <span style={{ opacity: 0.7 }}>
        ({data.permission})
      </span>
    </div>

    <pre
      style={{
        background: "#11161d",
        padding: 8,
        borderRadius: 4,
        fontSize: 12,
        maxHeight: 160,
        overflow: "auto",
        margin: "0 0 10px 0",
        whiteSpace: "pre-wrap",
      }}
    >
      {JSON.stringify(data.arguments ?? {}, null, 2)}
    </pre>

    <div style={{ display: "flex", gap: 8 }}>
      <button
        onClick={() => approve(aid, true)}
        style={{
          background: "#16a34a",
          color: "white",
          border: "none",
          borderRadius: 4,
          padding: "10px 20px",
          fontSize: 14,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        Approve
      </button>

      <button
        onClick={() => approve(aid, false)}
        style={{
          background: "#dc2626",
          color: "white",
          border: "none",
          borderRadius: 4,
          padding: "10px 20px",
          fontSize: 14,
          fontWeight: 700,
          cursor: "pointer",
        }}
      >
        Reject
      </button>
    </div>
  </div>
);
      })}
    </div>
  );
}


const inputStyle: React.CSSProperties = {
  background: "#11161d",

  color: "#e6edf3",

  border: "1px solid #2a313a",

  borderRadius: 4,

  padding: "6px 10px",

  fontFamily: "inherit",

  fontSize: 14,
};