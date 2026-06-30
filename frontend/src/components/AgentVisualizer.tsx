import React, { useEffect, useState } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { AgentName, AgentStatus } from '../types';
import { Cpu, Send, Zap, MessageSquare, Terminal } from 'lucide-react';

interface NodePosition {
  x: number;
  y: number;
  label: string;
}

const NODE_POSITIONS: Record<AgentName, NodePosition> = {
  LeadConsultant: { x: 50, y: 15, label: 'Lead Consultant' },
  Manager: { x: 50, y: 48, label: 'Project Manager' },
  PromptEngineer: { x: 20, y: 32, label: 'Prompt Engineer' },
  Coder: { x: 20, y: 68, label: 'Coder Agent' },
  Reviewer: { x: 80, y: 68, label: 'Reviewer Agent' },
  Tester: { x: 80, y: 32, label: 'Tester Agent' },
  Integrator: { x: 50, y: 85, label: 'Integrator Agent' },
};

// Alur kerja koneksi antar agent
const CONNECTIONS: { from: AgentName; to: AgentName }[] = [
  { from: 'LeadConsultant', to: 'Manager' },
  { from: 'Manager', to: 'PromptEngineer' },
  { from: 'PromptEngineer', to: 'Coder' },
  { from: 'Coder', to: 'Reviewer' },
  { from: 'Reviewer', to: 'Tester' },
  { from: 'Tester', to: 'Integrator' },
  { from: 'Integrator', to: 'LeadConsultant' },
];

const STATUS_NEON: Record<AgentStatus, { glow: string; border: string; bg: string; text: string }> = {
  IDLE: {
    glow: 'shadow-[0_0_15px_rgba(71,85,105,0.2)]',
    border: 'border-slate-700/60',
    bg: 'bg-slate-900/80',
    text: 'text-slate-400',
  },
  THINKING: {
    glow: 'shadow-[0_0_20px_rgba(168,85,247,0.5)] animate-pulse',
    border: 'border-purple-550/80',
    bg: 'bg-purple-950/20',
    text: 'text-purple-400',
  },
  WORKING: {
    glow: 'shadow-[0_0_20px_rgba(59,130,246,0.6)] animate-pulse',
    border: 'border-blue-500/80',
    bg: 'bg-blue-950/25',
    text: 'text-blue-400',
  },
  WAITING_REVIEW: {
    glow: 'shadow-[0_0_15px_rgba(236,72,153,0.5)]',
    border: 'border-pink-500/70',
    bg: 'bg-pink-950/20',
    text: 'text-pink-400',
  },
  WAITING_USER_INPUT: {
    glow: 'shadow-[0_0_20px_rgba(249,115,22,0.6)] animate-bounce',
    border: 'border-orange-500/80',
    bg: 'bg-orange-950/25',
    text: 'text-orange-400',
  },
  DONE: {
    glow: 'shadow-[0_0_15px_rgba(34,197,94,0.4)]',
    border: 'border-green-500/60',
    bg: 'bg-green-950/20',
    text: 'text-green-400',
  },
  BLOCKED: {
    glow: 'shadow-[0_0_20px_rgba(239,68,68,0.7)] animate-pulse',
    border: 'border-red-500/80',
    bg: 'bg-red-950/30',
    text: 'text-red-400',
  },
  ERROR: {
    glow: 'shadow-[0_0_25px_rgba(244,63,94,0.8)] animate-ping-slow',
    border: 'border-rose-600/80',
    bg: 'bg-rose-950/35',
    text: 'text-rose-400',
  },
};

export function AgentVisualizer() {
  const { agents, messages } = useSigmaStore();
  const [activeComm, setActiveComm] = useState<{ sender: string; receiver: string } | null>(null);

  // Deteksi pesan komunikasi terakhir yang aktif (< 6 detik yang lalu)
  useEffect(() => {
    if (messages.length === 0) return;
    const lastMsg = messages[messages.length - 1];
    
    // Pastikan pesan adalah komunikasi antar agent
    if (lastMsg.message_type === 'agent_comm') {
      const sender = lastMsg.metadata?.sender;
      const receiver = lastMsg.metadata?.receiver;
      if (sender && receiver) {
        setActiveComm({ sender, receiver });
        const timer = setTimeout(() => setActiveComm(null), 5000);
        return () => clearTimeout(timer);
      }
    }
  }, [messages]);

  // Helper untuk mendapatkan koordinat absolut SVG (skala 800 x 600)
  const getCoords = (name: AgentName) => {
    const pos = NODE_POSITIONS[name];
    if (!pos) return { x: 400, y: 300 };
    return {
      x: (pos.x / 100) * 800,
      y: (pos.y / 100) * 550,
    };
  };

  return (
    <div className="flex-1 h-full flex flex-col glass-panel p-6 rounded-2xl relative overflow-hidden bg-slate-950/30">
      {/* Detail Panel */}
      <div className="flex items-center justify-between shrink-0 mb-4 border-b border-slate-800/60 pb-3 relative z-15">
        <div>
          <h3 className="font-bold text-lg text-white tracking-tight flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-400 animate-pulse" />
            Visualisasi Tim Agent Interaktif
          </h3>
          <p className="text-xs text-slate-400">
            Alur komunikasi, status berpikir, dan kerja terisolasi secara real-time.
          </p>
        </div>
      </div>

      {/* SVG Canvas & Node Network */}
      <div className="flex-1 w-full relative min-h-[480px]">
        {/* Canvas SVG untuk render koneksi garis laser */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 800 550" preserveAspectRatio="xMidYMid meet">
          <defs>
            {/* Gradien neon dinamis */}
            <linearGradient id="laserGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="50%" stopColor="#8b5cf6" />
              <stop offset="100%" stopColor="#10b981" />
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>

          {/* Render garis koneksi */}
          {CONNECTIONS.map((conn, idx) => {
            const start = getCoords(conn.from);
            const end = getCoords(conn.to);
            
            // Cek apakah garis ini sedang aktif digunakan untuk komunikasi
            const isCommActive = activeComm && (
              (activeComm.sender === conn.from && activeComm.receiver === conn.to) ||
              (activeComm.sender === conn.to && activeComm.receiver === conn.from)
            );

            return (
              <g key={idx}>
                {/* Garis latar belakang redup */}
                <line
                  x1={start.x}
                  y1={start.y}
                  x2={end.x}
                  y2={end.y}
                  stroke="#1e293b"
                  strokeWidth="2.5"
                />
                
                {/* Garis laser bersinar jika aktif */}
                {isCommActive ? (
                  <>
                    <line
                      x1={start.x}
                      y1={start.y}
                      x2={end.x}
                      y2={end.y}
                      stroke="url(#laserGrad)"
                      strokeWidth="4"
                      filter="url(#glow)"
                      strokeDasharray="12,12"
                      className="animate-[dash_1.5s_linear_infinite]"
                      style={{
                        animation: 'dash 1.5s linear infinite'
                      }}
                    />
                    {/* Circle Pulse Indicator yang mengalir */}
                    <circle r="6" fill="#10b981" filter="url(#glow)">
                      <animateMotion
                        path={`M ${start.x} ${start.y} L ${end.x} ${end.y}`}
                        dur="1.5s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  </>
                ) : null}
              </g>
            );
          })}
        </svg>

        {/* CSS Animation inline untuk keyframe dashoffset */}
        <style dangerouslySetInnerHTML={{__html: `
          @keyframes dash {
            to {
              stroke-dashoffset: -40;
            }
          }
        `}} />

        {/* Render Card Node Agent secara absolut */}
        {Object.entries(NODE_POSITIONS).map(([name, pos]) => {
          const agentState = agents.find((a) => a.name === name);
          const status = agentState?.status || 'IDLE';
          const neon = STATUS_NEON[status] || STATUS_NEON.IDLE;
          const tokens = agentState?.token_count || 0;

          return (
            <div
              key={name}
              className="absolute shrink-0 w-44 -translate-x-1/2 -translate-y-1/2 transition-all duration-500"
              style={{ left: `${pos.x}%`, top: `${pos.y}%` }}
            >
              <div className={`p-3.5 rounded-2xl border ${neon.border} ${neon.bg} ${neon.glow} flex flex-col gap-2 relative group backdrop-blur-md`}>
                {/* Status dot pendar */}
                <span className="absolute top-2.5 right-2.5 flex h-2 w-2">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status === 'WORKING' ? 'bg-blue-400' : status === 'THINKING' ? 'bg-purple-400' : 'bg-slate-400'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2 w-2 ${status === 'WORKING' ? 'bg-blue-500' : status === 'THINKING' ? 'bg-purple-500' : 'bg-slate-500'}`}></span>
                </span>

                <div className="flex items-center gap-2">
                  <div className={`p-1.5 rounded-lg bg-slate-950/60 ${neon.text}`}>
                    <Cpu className="h-4.5 w-4.5" />
                  </div>
                  <div>
                    <h4 className="font-bold text-white text-xs leading-none">{pos.label}</h4>
                    <span className={`text-[8.5px] font-extrabold tracking-wide uppercase mt-1 inline-block ${neon.text}`}>
                      {status}
                    </span>
                  </div>
                </div>

                {agentState?.last_message ? (
                  <div className="text-[10px] text-slate-300 bg-slate-950/65 p-2 rounded-lg border border-slate-900 line-clamp-2 select-none">
                    {agentState.last_message}
                  </div>
                ) : (
                  <div className="text-[10px] text-slate-500 italic p-1">
                    Menunggu tugas...
                  </div>
                )}

                <div className="text-[9px] text-slate-500 font-mono text-right shrink-0">
                  {tokens.toLocaleString()} tokens
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
