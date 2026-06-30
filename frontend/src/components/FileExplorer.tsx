import React, { useEffect, useState } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { FileItem } from '../types';
import { api } from '../api';
import { Folder, File, RefreshCw, FolderOpen, HardDrive, Info } from 'lucide-react';

export function FileExplorer() {
  const { project } = useSigmaStore();
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchFiles = async () => {
    if (!project) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProjectFiles(project.project_id);
      setFiles(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFiles();
    // Auto-refresh daftar file setiap 5 detik agar real-time mengikuti progres agent coding
    const interval = setInterval(fetchFiles, 5000);
    return () => clearInterval(interval);
  }, [project?.project_id]);

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="glass-panel p-5 rounded-2xl flex flex-col h-full space-y-4 bg-slate-950/20">
      <div className="flex items-center justify-between border-b border-slate-850 pb-3 shrink-0">
        <div className="flex items-center gap-2">
          <HardDrive className="h-5 w-5 text-blue-400" />
          <div>
            <h3 className="font-bold text-sm text-white">Sandbox File Explorer</h3>
            <p className="text-[10px] text-slate-400">File & folder hasil pekerjaan agent secara live.</p>
          </div>
        </div>
        
        <button
          onClick={fetchFiles}
          disabled={loading}
          className="p-2 hover:bg-slate-900 border border-slate-800 rounded-lg transition text-slate-400 hover:text-white disabled:opacity-50 shrink-0"
          title="Refresh Berkas"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-blue-400' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="text-[11px] text-rose-400 bg-rose-500/10 p-2.5 rounded-lg border border-rose-500/20 shrink-0">
          Gagal memuat berkas: {error}
        </div>
      )}

      {/* Explorer List */}
      <div className="flex-1 overflow-y-auto pr-1">
        {files.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-500 text-xs py-10 space-y-2">
            <FolderOpen className="h-10 w-10 text-slate-700 animate-pulse" />
            <span>Workspace masih kosong.</span>
            <span className="text-[10px] text-slate-600 text-center px-6">Agent belum membuat berkas coding di sandbox.</span>
          </div>
        ) : (
          <div className="space-y-1">
            {files.map((file) => {
              // Hitung indentasi visual berdasarkan struktur path subfolder
              const depth = file.path.split('/').length - 1;
              const isNested = depth > 0;

              return (
                <div
                  key={file.path}
                  className="flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-900/50 border border-transparent hover:border-slate-850/50 transition duration-150 group text-xs cursor-default"
                  style={{ paddingLeft: `${10 + depth * 12}px` }}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {file.is_dir ? (
                      <Folder className="h-4 w-4 text-amber-400 shrink-0 fill-amber-400/10" />
                    ) : (
                      <File className="h-4 w-4 text-blue-400 shrink-0" />
                    )}
                    <span className="text-slate-200 font-medium truncate select-all">{file.name}</span>
                  </div>

                  {!file.is_dir && (
                    <div className="flex items-center gap-3 text-[10px] text-slate-500 shrink-0 font-mono">
                      <span>{formatSize(file.size)}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {project?.external_path && (
        <div className="flex items-start gap-2 bg-blue-500/5 border border-blue-500/10 rounded-xl p-3 shrink-0">
          <Info className="h-4 w-4 text-blue-400 mt-0.5 shrink-0" />
          <span className="text-[10px] text-slate-400 leading-normal">
            Menampilkan file dari direktori host: <br />
            <strong className="text-slate-300 select-all font-mono text-[9px]">{project.external_path}</strong>
          </span>
        </div>
      )}
    </div>
  );
}
