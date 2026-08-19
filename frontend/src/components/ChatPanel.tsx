import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { getChatHistory, sendChat } from "@/lib/api";
import type { MatchResultItem } from "@/types/api";

interface ChatPanelProps {
  sessionId: string | null;
  selected: MatchResultItem | null;
}

export function ChatPanel({ sessionId, selected }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);

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
    onSuccess: (data) => {
      setMessages(data.messages);
      setInput("");
    },
  });

  const handleSend = () => {
    if (!sessionId || !input.trim()) return;
    chatMutation.mutate({
      session_id: sessionId,
      message: input.trim(),
      result_id: selected?.id,
    });
  };

  return (
    <div className="chat-panel">
      <h3>Follow-up questions</h3>
      {!selected ? (
        <p className="muted">Select a ranked result to chat about that match.</p>
      ) : (
        <p className="muted">Asking about: {selected.job_filename}</p>
      )}

      <div className="chat-log">
        {messages.length === 0 ? (
          <p className="muted">Try: &quot;What should I emphasize for this role?&quot;</p>
        ) : (
          messages.map((msg, index) => (
            <div key={`${msg.role}-${index}`} className={`chat-bubble ${msg.role}`}>
              <strong>{msg.role === "user" ? "You" : "Assistant"}</strong>
              <p>{msg.content}</p>
            </div>
          ))
        )}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          value={input}
          placeholder="Ask about this match..."
          disabled={!sessionId || !selected || chatMutation.isPending}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") handleSend();
          }}
        />
        <button
          type="button"
          className="btn"
          disabled={!sessionId || !selected || chatMutation.isPending || !input.trim()}
          onClick={handleSend}
        >
          {chatMutation.isPending ? "..." : "Send"}
        </button>
      </div>
      {chatMutation.isError ? (
        <p className="error">{(chatMutation.error as Error).message}</p>
      ) : null}
    </div>
  );
}
