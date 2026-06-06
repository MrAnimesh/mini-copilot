import React, { useState } from "react";

import { Timeline } from "./components/Timeline";

import {
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
        margin: "auto",
        padding: 24,
      }}
    >
      <h1 style={{ marginTop: 0 }}>
        mini-copilot
      </h1>

      <p style={{ opacity: 0.7 }}>
        Offline agentic coding • powered by local Ollama
      </p>

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
                e.target.value as
                  | "manual"
                  | "auto-edit"
                  | "yolo"
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


const inputStyle: React.CSSProperties = {
  background: "#11161d",

  color: "#eee",

  border: "1px solid #2a313a",

  borderRadius: 4,

  padding: "6px 10px",

  fontFamily: "inherit",

  fontSize: 14,
};