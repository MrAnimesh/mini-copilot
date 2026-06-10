// Minimal SSE client built on fetch + ReadableStream
// so we can POST a body.
// (Browser EventSource is GET-only.)

export type AgentEvent = {
  type: string;
  step: number;
  data: Record<string, unknown>;
};

export async function* streamAgent(
  url: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<AgentEvent> {
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!resp.ok || !resp.body) {
    throw new Error(`agent run failed: ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();

  let buf = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    buf += decoder.decode(value, { stream: true });

    // Extract all complete "data:" lines from the buffer.
    // SSE spec says frames are separated by \n\n, but sse-starlette sometimes
    // concatenates them. We use a regex to pull every "data: {...}" payload.
    const lines = buf.split("\n");

    const remaining: string[] = [];

    for (const line of lines) {
      const trimmed = line.trim();

      if (trimmed.startsWith("data:")) {
        const payload = trimmed.slice(5).trim();

        if (!payload || payload.startsWith("- ")) {
          // ping or empty data line
          continue;
        }

        try {
          const ev = JSON.parse(payload) as AgentEvent;

          console.log("[sse] yielding", ev.type, ev.step);

          yield ev;
        } catch {
          // Incomplete JSON - put it back and wait for more data
          remaining.push(line);
        }
      } else if (
        trimmed.startsWith("event:") ||
        trimmed === "" ||
        trimmed.startsWith(": ping")
      ) {
        // SSE event type line or comment - skip
        continue;
      } else if (trimmed) {
        // Possibly a continuation of incomplete data - keep it
        remaining.push(line);
      }
    }

    buf = remaining.join("\n");
  }
  if (buf.trim()) {
    const lastLine = buf.trim();

    if (lastLine.startsWith("data:")) {
      try {
        const ev = JSON.parse(
          lastLine.slice(5).trim()
        ) as AgentEvent;

        console.log(
          "[sse] yielding (final)",
          ev.type,
          ev.step
        );

        yield ev;
      } catch {
        /* ignore */
      }
    }
  }

  console.log("[sse] stream ended");
}

export async function approve(
  approvalId: string,
  approved: boolean,
): Promise<void> {
  await fetch("http://localhost:8765/agent/approve", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      approval_id: approvalId,
      approved,
    }),
  });
}