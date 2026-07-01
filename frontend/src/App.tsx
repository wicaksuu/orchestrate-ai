import React, { useEffect, useState } from 'react';
import { useSigmaStore } from './store/sigmaStore';
import { useWebSocket } from './hooks/useWebSocket';
import { EscalationBanner } from './components/EscalationBanner';
import { ChatWindow } from './components/ChatWindow';
import { AgentDashboard } from './components/AgentDashboard';
import { CommLog } from './components/CommLog';
import { TeamConfigPanel } from './components/TeamConfigPanel';
import { AgentVisualizer } from './components/AgentVisualizer';
import { FileExplorer } from './components/FileExplorer';
import { Cpu, Plus, FolderGit, MessageSquare, Zap, Settings, LogOut, Terminal, LayoutGrid, Sidebar, Eye, EyeOff, Trash2, Edit2, Check, X } from 'lucide-react';

export default function App() {
  const { project, projectList, fetchProjectList, initProject, loadProject, deleteProject, updateProjectDetails, loading, error } = useSigmaStore();
  const [projName, setProjName] = useState('');
  const [projDesc, setProjDesc] = useState('');
  const [projExtPath, setProjExtPath] = useState('');
  const [activeTab, setActiveTab] = useState<'workspace' | 'visualizer' | 'settings'>('workspace');

  // Edit state
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editDesc, setEditDesc] = useState('');
  
  // Selection state
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);

  // Collapsible panel states for responsiveness
  const [showFileExplorer, setShowFileExplorer] = useState(true);
  const [showCommLog, setShowCommLog] = useState(true);

  // Auto-connect WebSocket saat project sudah terbuat/di-load
  useWebSocket(project?.project_id);

  // Inisialisasi otomatis default project jika tidak ada project tersimpan
  useEffect(() => {
    fetchProjectList(); // Muat histori dari backend
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
    await initProject(projName, projDesc, projExtPath);
  };

  // 1. Tampilan jika project belum terbuat
  if (!project) {
    return (
      <div className="min-h-screen bg-[#070a13] flex flex-col items-center justify-center p-6 relative overflow-hidden">
        {/* Ambient background decoration */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[100px] pointer-events-none"></div>
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-[100px] pointer-events-none"></div>

        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
          {/* Kolom Kiri: Form Buat Proyek Baru */}
          <div className="glass-panel p-8 rounded-2xl space-y-6">
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

              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Path Direktori Lokal (Opsional)
                </label>
                <input
                  type="text"
                  value={projExtPath}
                  onChange={(e) => setProjExtPath(e.target.value)}
                  placeholder="misal: /Users/username/Documents/my-project"
                  className="w-full bg-slate-950/80 border border-slate-800 hover:border-slate-700 focus:border-blue-500 text-white rounded-xl px-4 py-3 text-sm outline-none transition"
                />
                <p className="text-[10px] text-slate-500">
                  Penting: Pastikan path ini berada di bawah direktori home Anda (/Users).
                </p>
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

          {/* Kolom Kanan: Riwayat Proyek */}
          <div className="glass-panel p-8 rounded-2xl flex flex-col max-h-[600px]">
            <div className="flex justify-between items-center mb-4">
              <div className="flex items-center gap-3">
                {projectList.length > 0 && (
                  <input 
                    type="checkbox"
                    checked={projectList.length > 0 && selectedProjects.length === projectList.length}
                    onChange={(e) => {
                      if (e.target.checked) setSelectedProjects(projectList.map(p => p.project_id));
                      else setSelectedProjects([]);
                    }}
                    className="w-4 h-4 rounded border-slate-700 bg-slate-800 accent-blue-500 cursor-pointer"
                    title="Pilih Semua"
                  />
                )}
                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                  <FolderGit className="h-5 w-5 text-blue-400" /> Riwayat Proyek
                </h2>
              </div>
              {selectedProjects.length > 0 && (
                <button
                  onClick={async () => {
                    if (window.confirm(`Hapus permanen ${selectedProjects.length} proyek terpilih beserta isinya?`)) {
                      for (const pid of selectedProjects) {
                        try {
                          await deleteProject(pid);
                        } catch(e) {
                          console.error("Gagal hapus", pid);
                        }
                      }
                      setSelectedProjects([]);
                    }
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/20 text-rose-400 hover:bg-rose-500/30 hover:text-rose-300 rounded-lg text-xs transition"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Hapus ({selectedProjects.length})
                </button>
              )}
            </div>
            <div className="flex-1 overflow-y-auto pr-2 space-y-3 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
              {projectList.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-slate-500">
                  <FolderGit className="h-10 w-10 mb-2 opacity-50" />
                  <p className="text-sm">Belum ada proyek.</p>
                </div>
              ) : (
                projectList.map((p) => (
                  <div key={p.project_id} className="relative w-full flex gap-3 p-4 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-blue-500/50 hover:bg-blue-900/20 transition group">
                    <div className="relative z-20 flex items-start pt-1">
                      <input 
                        type="checkbox" 
                        checked={selectedProjects.includes(p.project_id)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedProjects([...selectedProjects, p.project_id]);
                          else setSelectedProjects(selectedProjects.filter(id => id !== p.project_id));
                        }}
                        className="w-4 h-4 rounded border-slate-700 bg-slate-800 accent-blue-500 cursor-pointer"
                      />
                    </div>
                    <div className="flex-1 min-w-0">
                    {editingProjectId === p.project_id ? (
                      <div className="space-y-3 relative z-20">
                        <input
                          autoFocus
                          value={editName}
                          onChange={(e) => setEditName(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-700 text-white rounded p-2 text-sm outline-none"
                        />
                        <textarea
                          value={editDesc}
                          onChange={(e) => setEditDesc(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-700 text-slate-400 rounded p-2 text-xs outline-none"
                          rows={2}
                        />
                        <div className="flex gap-2 justify-end">
                          <button onClick={() => setEditingProjectId(null)} className="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300">
                            <X className="w-4 h-4" />
                          </button>
                          <button onClick={() => {
                            updateProjectDetails(p.project_id, editName, editDesc);
                            setEditingProjectId(null);
                          }} className="p-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white">
                            <Check className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div 
                          onClick={() => loadProject(p.project_id)}
                          className="absolute inset-0 cursor-pointer z-0 rounded-xl"
                        ></div>
                        <div className="flex justify-between items-start mb-1 relative z-10 pointer-events-none">
                          <h3 className="text-sm font-semibold text-white group-hover:text-blue-300 transition">{p.name}</h3>
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                            {p.status}
                          </span>
                        </div>
                        {p.description && (
                          <p className="text-xs text-slate-400 line-clamp-2 relative z-10 pointer-events-none">{p.description}</p>
                        )}
                        <div className="mt-3 flex justify-between items-center relative z-10">
                          <span className="text-[10px] text-slate-500 pointer-events-none">
                            {new Date(p.updated_at).toLocaleString('id-ID')}
                          </span>
                          <div className="flex opacity-0 group-hover:opacity-100 transition-opacity gap-2">
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditName(p.name);
                                setEditDesc(p.description || '');
                                setEditingProjectId(p.project_id);
                              }}
                              className="p-1.5 rounded hover:bg-slate-700/50 text-slate-400 hover:text-blue-400 transition"
                              title="Edit Proyek"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                if (window.confirm(`Hapus permanen proyek "${p.name}" beserta seluruh isinya?`)) {
                                  deleteProject(p.project_id);
                                }
                              }}
                              className="p-1.5 rounded hover:bg-rose-500/20 text-slate-400 hover:text-rose-400 transition"
                              title="Hapus Proyek"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </div>
                      </>
                    )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 2. Tampilan dashboard utama dengan Sidebar Kiri Modern & Grid Responsif
  return (
    <div className="h-screen w-screen flex bg-[#070a13] text-[#e2e8f0] overflow-hidden">
      
      {/* SIDEBAR NAVIGASI KIRI */}
      <aside className="w-64 border-r border-slate-850 bg-slate-950/70 backdrop-blur-md flex flex-col shrink-0">
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-slate-850 gap-3">
          <div className="p-1.5 bg-blue-600/10 border border-blue-500/20 rounded-lg text-blue-400">
            <Cpu className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <h1 className="font-bold text-white tracking-tight flex items-center gap-1.5">
              SIGMA
              <span className="text-[9px] bg-slate-800 text-slate-400 font-mono px-1.5 py-0.5 rounded border border-slate-700">
                v1.0
              </span>
            </h1>
          </div>
        </div>

        {/* Info Proyek Aktif */}
        <div className="p-4 border-b border-slate-850 bg-slate-900/10">
          <div className="flex flex-col gap-1 p-3 bg-slate-900/50 border border-slate-800 rounded-xl">
            <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Proyek Aktif</span>
            <div className="flex items-center gap-2 text-white font-semibold text-xs truncate">
              <FolderGit className="h-4 w-4 text-blue-400 shrink-0" />
              <span className="truncate">{project.name}</span>
            </div>
            <span className="text-[9px] text-slate-400 font-mono capitalize">Status: {project.status}</span>
          </div>
        </div>

        {/* Menu Navigasi */}
        <nav className="flex-1 p-4 space-y-1.5">
          <button
            onClick={() => setActiveTab('workspace')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab === 'workspace' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30' : 'text-slate-400 hover:text-white hover:bg-slate-900/40'}`}
          >
            <MessageSquare className="h-4.5 w-4.5" />
            Workspace Chat
          </button>
          
          <button
            onClick={() => setActiveTab('visualizer')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab === 'visualizer' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30' : 'text-slate-400 hover:text-white hover:bg-slate-900/40'}`}
          >
            <Zap className="h-4.5 w-4.5" />
            Visualizer Tim
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition ${activeTab === 'settings' ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/30' : 'text-slate-400 hover:text-white hover:bg-slate-900/40'}`}
          >
            <Settings className="h-4.5 w-4.5" />
            Konfigurasi AI
          </button>
        </nav>

        {/* Footer Sidebar (Keluar/Beralih Proyek) */}
        <div className="p-4 border-t border-slate-850">
          <button
            onClick={() => {
              localStorage.removeItem('sigma_active_project_id');
              window.location.reload();
            }}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white rounded-xl text-xs font-semibold transition border border-slate-800 hover:border-slate-700"
          >
            <LogOut className="h-4 w-4" />
            Beralih Proyek
          </button>
        </div>
      </aside>

      {/* WINDOW HARI / KONTEN UTAMA */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Escalation Banner */}
        <EscalationBanner />

        {/* Toolbar responsivitas atas jika tab workspace aktif */}
        {activeTab === 'workspace' && (
          <div className="h-12 border-b border-slate-850 px-6 flex items-center justify-end gap-3 bg-slate-950/20 shrink-0 select-none">
            <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mr-auto">Workspace Control</span>
            
            {/* Toggle Comm Log */}
            <button
              onClick={() => setShowCommLog(!showCommLog)}
              className={`p-1.5 border rounded-lg transition text-xs flex items-center gap-1.5 font-semibold ${showCommLog ? 'bg-slate-900 border-slate-800 text-white' : 'bg-transparent border-transparent text-slate-500 hover:text-slate-350'}`}
              title={showCommLog ? 'Sembunyikan Log Komunikasi' : 'Tampilkan Log Komunikasi'}
            >
              <Terminal className="h-4 w-4" />
              <span>Log</span>
            </button>

            {/* Toggle File Explorer */}
            <button
              onClick={() => setShowFileExplorer(!showFileExplorer)}
              className={`p-1.5 border rounded-lg transition text-xs flex items-center gap-1.5 font-semibold ${showFileExplorer ? 'bg-slate-900 border-slate-800 text-white' : 'bg-transparent border-transparent text-slate-500 hover:text-slate-350'}`}
              title={showFileExplorer ? 'Sembunyikan File Explorer' : 'Tampilkan File Explorer'}
            >
              <Sidebar className="h-4 w-4" />
              <span>Explorer</span>
            </button>
          </div>
        )}

        {/* Konten Halaman Berdasarkan Tab */}
        <div className="flex-1 flex overflow-hidden p-4 lg:p-6">
          {activeTab === 'workspace' && (
            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden gap-4 lg:gap-6">
              
              {/* Kolom 1: Chat Window (Lebar dinamis responsif) */}
              <div className="w-full lg:w-[350px] xl:w-[380px] shrink-0 h-full flex flex-col transition-all duration-300">
                <ChatWindow />
              </div>

              {/* Kolom 2: Dashboard & Logs (Mengambil sisa ruang tengah) */}
              <div className="flex-1 flex flex-col gap-4 lg:gap-6 h-full overflow-hidden transition-all duration-300">
                {/* Agent Dashboard Grid */}
                <div className="flex-1 overflow-y-auto pr-1">
                  <AgentDashboard />
                </div>
                
                {/* Comm Log (Collapsible dengan transisi mulus) */}
                <div
                  className={`shrink-0 overflow-hidden transition-all duration-350 ease-in-out ${showCommLog ? 'h-[250px] opacity-100' : 'h-0 opacity-0 pointer-events-none'}`}
                >
                  <CommLog />
                </div>
              </div>

              {/* Kolom 3: File Explorer (Collapsible dengan transisi mulus) */}
              <div
                className={`shrink-0 overflow-hidden transition-all duration-350 ease-in-out ${showFileExplorer ? 'w-full lg:w-76 xl:w-80 opacity-100' : 'w-0 opacity-0 pointer-events-none'}`}
              >
                <div className="h-full w-full min-w-[280px]">
                  <FileExplorer />
                </div>
              </div>
              
            </div>
          )}

          {activeTab === 'visualizer' && (
            <AgentVisualizer />
          )}

          {activeTab === 'settings' && (
            <div className="w-full max-w-4xl mx-auto h-full overflow-y-auto">
              <TeamConfigPanel />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
