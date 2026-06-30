import React, { useEffect, useState } from 'react';
import { useSigmaStore } from './store/sigmaStore';
import { useWebSocket } from './hooks/useWebSocket';
import { EscalationBanner } from './components/EscalationBanner';
import { ChatWindow } from './components/ChatWindow';
import { AgentDashboard } from './components/AgentDashboard';
import { CommLog } from './components/CommLog';
import { TeamConfigPanel } from './components/TeamConfigPanel';
import { Cpu, Terminal, Plus, FolderGit } from 'lucide-react';

export default function App() {
  const { project, initProject, loadProject, loading, error } = useSigmaStore();
  const [projName, setProjName] = useState('');
  const [projDesc, setProjDesc] = useState('');

  // Auto-connect WebSocket saat project sudah terbuat/di-load
  useWebSocket(project?.project_id);

  // Inisialisasi otomatis default project jika tidak ada project tersimpan
  useEffect(() => {
    // Sebagai alternatif, kita bisa buat default project agar user langsung masuk ke dashboard
    const cachedProjId = localStorage.getItem('sigma_active_project_id');
    if (cachedProjId) {
      loadProject(cachedProjId);
    }
  }, []);

  useEffect(() => {
    if (project) {
      localStorage.setItem('sigma_active_project_id', project.project_id);
    }
  }, [project]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projName.trim()) return;
    await initProject(projName, projDesc);
  };

  // 1. Tampilan jika project belum terbuat
  if (!project) {
    return (
      <div className="min-h-screen bg-[#070a13] flex flex-col items-center justify-center p-6 relative overflow-hidden">
        {/* Ambient background decoration */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="w-full max-w-md glass-panel p-8 rounded-2xl relative z-10 space-y-6">
          <div className="text-center space-y-2">
            <div className="inline-flex p-3 bg-blue-600/10 rounded-xl text-blue-400 mb-2 border border-blue-500/10">
              <Cpu className="h-8 w-8 animate-pulse" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">SIGMA Platform</h1>
            <p className="text-sm text-slate-400">
              Supervised Intelligent Group of Multi-Agents
            </p>
          </div>

          <form onSubmit={handleCreate} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Nama Proyek
              </label>
              <input
                type="text"
                value={projName}
                onChange={(e) => setProjName(e.target.value)}
                placeholder="misal: Driver YZ125 STM32"
                required
                className="w-full bg-slate-950/80 border border-slate-800 hover:border-slate-700 focus:border-blue-500 text-white rounded-xl px-4 py-3 text-sm outline-none transition"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Deskripsi Singkat
              </label>
              <textarea
                value={projDesc}
                onChange={(e) => setProjDesc(e.target.value)}
                placeholder="Spesifikasi modul atau goal utama proyek..."
                rows={3}
                className="w-full bg-slate-950/80 border border-slate-800 hover:border-slate-700 focus:border-blue-500 text-white rounded-xl px-4 py-3 text-sm outline-none transition"
              />
            </div>

            {error && (
              <p className="text-xs text-rose-500 bg-rose-500/10 p-3 rounded-lg border border-rose-500/20">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 px-4 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition active:scale-95 shadow-lg shadow-blue-900/30 disabled:opacity-50"
            >
              {loading ? (
                <span>Membuat Proyek...</span>
              ) : (
                <>
                  <Plus className="h-4.5 w-4.5" />
                  Mulai Proyek Baru
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // 2. Tampilan dashboard utama saat project siap
  return (
    <div className="h-screen w-screen flex flex-col bg-[#070a13] text-[#e2e8f0] overflow-hidden">
      {/* Escalation Banner */}
      <EscalationBanner />

      {/* Top Navigation */}
      <header className="h-16 border-b border-slate-850 px-6 flex items-center justify-between shrink-0 bg-slate-950/45 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-blue-600/10 border border-blue-500/20 rounded-lg text-blue-400">
            <Cpu className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-bold text-white tracking-tight flex items-center gap-2">
              SIGMA Platform
              <span className="text-[10px] bg-slate-800 text-slate-400 font-mono px-2 py-0.5 rounded border border-slate-700">
                MVP v1.0
              </span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/60 border border-slate-800 rounded-lg">
            <FolderGit className="h-4 w-4 text-blue-400" />
            <span className="text-white font-medium">{project.name}</span>
          </div>
          
          <button
            onClick={() => {
              localStorage.removeItem('sigma_active_project_id');
              window.location.reload();
            }}
            className="p-2 hover:bg-slate-900 border border-transparent hover:border-slate-800 rounded-lg transition text-slate-400 hover:text-white"
            title="Keluar / Beralih Proyek"
          >
            Beralih Proyek
          </button>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-1 flex overflow-hidden p-6 gap-6">
        {/* Left: Chat Lead Consultant */}
        <div className="w-1/3 min-w-[360px] h-full">
          <ChatWindow />
        </div>

        {/* Center: Agent Dashboard & Logs */}
        <div className="flex-1 flex flex-col gap-6 h-full overflow-hidden">
          {/* Top: Agent Dashboard Grid */}
          <div className="flex-1 overflow-y-auto">
            <AgentDashboard />
          </div>
          {/* Bottom: Comm Log */}
          <div className="h-[280px] shrink-0">
            <CommLog />
          </div>
        </div>

        {/* Right: Team Config Sidebar */}
        <div className="w-80 shrink-0 h-full">
          <TeamConfigPanel />
        </div>
      </div>
    </div>
  );
}
