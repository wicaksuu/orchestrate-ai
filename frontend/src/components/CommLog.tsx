import React, { useState } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { AgentMessage } from '../types';
import { MessageSquare, ArrowRight, Code } from 'lucide-react';

function LogEntryRow({ log }: { log: AgentMessage }) {
  const [showRaw, setShowRaw] = useState(false);

  return (
    <div className="p-3 bg-slate-900/30 hover:bg-slate-900/50 border border-slate-800/60 rounded-lg flex flex-col gap-2 transition duration-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <span className="px-2 py-0.5 bg-slate-800 text-blue-400 font-semibold rounded">
            {log.metadata.sender}
          </span>
          <ArrowRight className="h-3 w-3 text-slate-500" />
          <span className="px-2 py-0.5 bg-slate-800 text-purple-400 font-semibold rounded">
            {log.metadata.receiver}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-500">
            {new Date(log.timestamp).toLocaleTimeString()}
          </span>
          <button
            onClick={() => setShowRaw(!showRaw)}
            className={`p-1 rounded text-slate-500 hover:text-slate-300 hover:bg-slate-800 transition ${
              showRaw ? 'text-blue-400 bg-slate-800/80' : ''
            }`}
            title="Tampilkan JSON Mentah"
          >
            <Code className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {showRaw ? (
        <pre className="text-[10px] bg-slate-950 p-2.5 rounded-lg border border-slate-900 overflow-x-auto text-green-400 font-mono">
          {JSON.stringify(log, null, 2)}
        </pre>
      ) : (
        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          {log.content}
        </p>
      )}
    </div>
  );
}

export function CommLog() {
  const { messages } = useSigmaStore();
  
  // Filter khusus pesan antar-agent
  const agentLogs = messages.filter(
    (m) => m.message_type === 'agent_comm' || m.message_type === 'system'
  );

  return (
    <div className="flex flex-col h-full glass-panel rounded-xl overflow-hidden p-6 space-y-4">
      <div className="flex items-center gap-2">
        <MessageSquare className="h-5 w-5 text-purple-400" />
        <h3 className="font-semibold text-white">Communication Log</h3>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
        {agentLogs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center text-slate-500">
            <p className="text-xs font-mono">Menunggu komunikasi agent dimulai...</p>
          </div>
        ) : (
          [...agentLogs].reverse().map((log) => (
            <LogEntryRow key={log.id} log={log} />
          ))
        )}
      </div>
    </div>
  );
}
