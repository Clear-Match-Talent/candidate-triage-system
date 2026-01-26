"use client";

import { useState, useEffect, useRef } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

interface ChatSidebarProps {
  runId: string;
  onClose?: () => void;
}

export default function ChatSidebar({ runId, onClose }: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchChatHistory();
  }, [runId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchChatHistory = async () => {
    try {
      const response = await fetch(`/api/runs/${runId}/chat`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error("Error fetching chat history:", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || sending) return;

    const userMessage: Message = {
      role: "user",
      content: input,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {
      const response = await fetch(`/api/runs/${runId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: input }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data && data.response) {
          const assistantMessage: Message = {
            role: "assistant",
            content: data.response,
            timestamp: Date.now(),
          };
          setMessages((prev) => [...prev, assistantMessage]);
        } else {
          console.error("Invalid response format:", data);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content: `Error: Invalid response format - ${JSON.stringify(data)}`,
              timestamp: Date.now(),
            },
          ]);
        }
      } else {
        const errorText = await response.text();
        console.error("Response not OK:", response.status, errorText);
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: Failed to get response (${response.status})`,
            timestamp: Date.now(),
          },
        ]);
      }
    } catch (err) {
      console.error("Error sending message:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : 'Connection failed'}`,
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-l border-gray-200">
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <h3 className="font-semibold text-gray-900">Data Assistant</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 text-sm mt-8">
            <p>Ask questions about the standardized data,</p>
            <p>or report issues that need fixing.</p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-black"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-gray-200">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type a message..."
            className="flex-1 px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
            rows={2}
            disabled={sending}
          />
          <button
            onClick={sendMessage}
            disabled={sending || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
