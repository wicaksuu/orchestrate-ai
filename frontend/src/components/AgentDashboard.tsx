import React from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { AgentState } from '../types';
import { Cpu, CheckCircle, RefreshCw, AlertTriangle, Play, HelpCircle, FileText } from 'lucide-react';

const STATUS_CONFIGS: Record<string, { color: string; bg: string; anim: string }> = {
  IDLE: { color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-700/50', anim: '' },
  THINKING: { color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-650/40', anim: 'animate-pulse-slow' },
  WORKING: { color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-550/40', anim: 'animate-pulse-fast' },
  WAITING_REVIEW: { color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-650/40', anim: 'animate-pulse' },
  WAITING_USER_INPUT: { color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-650/40', anim: 'animate-bounce' },
  DONE: { color: 'text-green-400', bg: 'bg-green-500/10 border-green-650/40', anim: '' },
  BLOCKED: { color: 'text-red-400', bg: 'bg-red-500/10 border-red-650/40', anim: 'animate-shake' },
  ERROR: { color: 'text-rose-500', bg: 'bg-rose-500/15 border-rose-650/40', anim: 'animate-pulse' },
};

function AgentCard({ agent }: { agent: AgentState }) {
  const cfg = STATUS_CONFIGS[agent.status] || STATUS_CONFIGS.IDLE;

  return (
    <div className={`p-3.5 rounded-xl border glass-card transition-all duration-300 hover:scale-[1.02] ${cfg.bg} ${cfg.anim} flex flex-col justify-between h-full`}>
      <div>
        <div className="flex items-center justify-between gap-2 border-b border-slate-900/20 pb-2 shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <div className={`p-1.5 rounded-lg bg-slate-900/60 ${cfg.color} shrink-0`}>
              <Cpu className="h-4.5 w-4.5" />
            </div>
            <div className="min-w-0">
              <h4 className="font-semibold text-white text-xs truncate" title={agent.name}>{agent.name}</h4>
              <span className={`inline-flex items-center gap-1 text-[9px] font-extrabold tracking-wide uppercase mt-0.5 ${cfg.color}`}>
                {agent.status}
              </span>
            </div>
          </div>
          <div className="text-[9px] text-slate-400 bg-slate-950/80 px-2 py-0.5 rounded-md border border-slate-900/60 font-mono shrink-0">
            {agent.token_count.toLocaleString()} tok
          </div>
        </div>

        {agent.last_message && (
          <div className="mt-2.5 text-[11px] bg-slate-950/60 p-2 rounded-lg text-slate-300 border border-slate-900 line-clamp-2 leading-relaxed">
            {agent.last_message}
          </div>
        )}
      </div>
    </div>
  );
}

export function AgentDashboard() {
  const { agents } = useSigmaStore();

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-lg text-white">Agent Dashboard</h3>
        <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-900/60 border border-slate-800 px-3 py-1.5 rounded-lg">
          <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          <span>Real-time Sync</span>
        </div>
      </div>

      {/* Grid of cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <AgentCard key={agent.name} agent={agent} />
        ))}
      </div>
    </div>
  );
}
