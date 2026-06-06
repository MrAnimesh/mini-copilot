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

    if (done) {
      break;
    }

    buf += decoder.decode(value, { stream: true });

    let idx: number;

    while ((idx = buf.indexOf("\n\n")) !== -1) {
      const frame = buf.slice(0, idx);

      buf = buf.slice(idx + 2);

      const dataLine = frame
        .split("\n")
        .find((line) => line.startsWith("data:"));

      if (!dataLine) {
        continue;
      }

      try {
        yield JSON.parse(
          dataLine.slice(5).trim(),
        ) as AgentEvent;
      } catch {
        // Ignore malformed SSE frames
      }
    }
  }
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