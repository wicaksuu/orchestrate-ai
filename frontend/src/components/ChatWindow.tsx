import React, { useState, useRef, useEffect } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { Send, Bot, User } from 'lucide-react';

export function ChatWindow() {
  const { messages, sendMessage } = useSigmaStore();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Filter pesan chat saja (User <-> LeadConsultant)
  const chatMessages = messages.filter(
    (m) =>
      m.message_type === 'user' ||
      (m.metadata.sender === 'LeadConsultant' && m.metadata.receiver === 'User')
  );

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatMessages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const content = input;
    setInput('');
    await sendMessage(content);
  };

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-slate-900/80 border-b border-slate-800/80 flex items-center gap-3">
        <div className="p-2 bg-blue-500/10 rounded-lg text-blue-400">
          <Bot className="h-6 w-6 animate-pulse" />
        </div>
        <div>
          <h3 className="font-semibold text-white">Lead Consultant</h3>
          <p className="text-xs text-green-400 flex items-center gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-green-400 animate-ping"></span>
            Online
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {chatMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 px-4">
            <Bot className="h-12 w-12 mb-3 text-slate-500 opacity-60" />
            <p className="text-sm font-medium">Belum ada obrolan dengan Lead Consultant.</p>
            <p className="text-xs text-slate-500 mt-1">Mulailah dengan menyapa "Halo" atau tanyakan rekomendasi tim.</p>
          </div>
        ) : (
          chatMessages.map((msg) => {
            const isUser = msg.message_type === 'user';
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${
                  isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
                }`}
              >
                <div
                  className={`p-2 h-9 w-9 rounded-lg flex items-center justify-center shrink-0 ${
                    isUser ? 'bg-blue-600 text-white' : 'bg-slate-850 border border-slate-700 text-blue-400'
                  }`}
                >
                  {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
                </div>

                <div
                  className={`p-4 rounded-2xl text-sm ${
                    isUser
                      ? 'bg-blue-600 text-white rounded-tr-none'
                      : 'bg-slate-800/80 text-slate-200 border border-slate-700/50 rounded-tl-none'
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  <span className="block text-[10px] text-right mt-1.5 opacity-60">
                    {new Date(msg.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="p-4 bg-slate-900/60 border-t border-slate-800/85 flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tulis pesan ke Lead Consultant..."
          className="flex-1 bg-slate-950 border border-slate-800 hover:border-slate-700/80 focus:border-blue-500 text-white placeholder-slate-500 rounded-xl px-4 py-3 text-sm outline-none transition"
        />
        <button
          type="submit"
          disabled={!input.trim()}
          className="p-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl transition active:scale-95 disabled:opacity-50 disabled:active:scale-100"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
