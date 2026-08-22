import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getChatHistory, sendChat } from "@/lib/api";
import type { MatchResultItem } from "@/types/api";

interface ChatPanelProps {
  sessionId: string | null;
  selected: MatchResultItem | null;
}

type Message = { role: string; content: string };

export function ChatPanel({ sessionId, selected }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const historyQuery = useQuery({
    queryKey: ["chat", sessionId],
    queryFn: () => getChatHistory(sessionId!),
    enabled: Boolean(sessionId),
  });

  useEffect(() => {
    if (historyQuery.data?.messages) {
      setMessages(historyQuery.data.messages);
    } else if (!sessionId) {
      setMessages([]);
    }
  }, [historyQuery.data, sessionId]);

  const chatMutation = useMutation({
    mutationFn: sendChat,
    // The reply takes a while, so the question is shown straight away rather
    // than only appearing once the whole exchange comes back.
    onMutate: ({ message }) => {
      setMessages((prev) => [...prev, { role: "user", content: message }]);
      setInput("");
    },
    onSuccess: (data) => setMessages(data.messages),
    onError: () => setMessages((prev) => prev.slice(0, -1)),
  });

  const pending = chatMutation.isPending;

  // Keep the newest message in view, including while the reply is typing.
  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages, pending]);

  const handleSend = () => {
    const message = input.trim();
    if (!sessionId || !selected || !message || pending) return;
    chatMutation.mutate({ session_id: sessionId, message, result_id: selected.id });
  };

  return (
    <div className="chat-panel">
      <h3>Follow-up questions</h3>

      <div className="chat-log" ref={logRef}>
        {messages.length === 0 && !pending ? (
          <p className="muted small-hint">
            {selected
              ? 'Try: "What should I emphasise for this role?"'
              : "Select a ranked job to chat about that match."}
          </p>
        ) : (
          messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className={`bubble ${msg.role}`}>
              {msg.content}
            </div>
          ))
        )}

        {pending ? (
          <div className="bubble assistant typing" aria-label="Assistant is typing">
            <span />
            <span />
            <span />
          </div>
        ) : null}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          placeholder={selected ? "Ask about this match..." : "Select a job first"}
          disabled={!sessionId || !selected || pending}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
        />
        <button
          type="button"
          className="btn primary"
          disabled={!sessionId || !selected || pending || !input.trim()}
          onClick={handleSend}
        >
          Send
        </button>
      </div>

      {chatMutation.isError ? (
        <p className="error small-hint">{(chatMutation.error as Error).message}</p>
      ) : null}
    </div>
  );
}
