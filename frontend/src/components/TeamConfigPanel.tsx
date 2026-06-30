import React, { useState, useEffect } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { Settings, Save, Check } from 'lucide-react';

export function TeamConfigPanel() {
  const { teamConfig, updateConfig } = useSigmaStore();
  const [coderCount, setCoderCount] = useState(1);
  const [activeRoles, setActiveRoles] = useState<Record<string, boolean>>({});
  const [models, setModels] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (teamConfig) {
      setCoderCount(teamConfig.coder_count);
      setActiveRoles(teamConfig.active_roles);
      setModels(teamConfig.models);
    }
  }, [teamConfig]);

  const handleSave = async () => {
    if (!teamConfig) return;
    const updated = {
      coder_count: coderCount,
      active_roles: activeRoles,
      models: models,
    };
    await updateConfig(updated);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  if (!teamConfig) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs font-mono">
        Loading Team Config...
      </div>
    );
  }

  return (
    <div className="glass-panel p-6 rounded-xl flex flex-col h-full space-y-5 overflow-y-auto">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
        <Settings className="h-5 w-5 text-blue-400" />
        <h3 className="font-semibold text-white">Konfigurasi Tim</h3>
      </div>

      {/* Coder count */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Jumlah Coder ({coderCount})
        </label>
        <input
          type="range"
          min="1"
          max="5"
          value={coderCount}
          onChange={(e) => setCoderCount(parseInt(e.target.value))}
          className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
      </div>

      {/* Active roles */}
      <div className="space-y-3">
        <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Role Aktif
        </span>
        <div className="space-y-2">
          {Object.entries(activeRoles).map(([role, active]) => (
            <label key={role} className="flex items-center gap-2.5 text-sm cursor-pointer select-none">
              <input
                type="checkbox"
                checked={active}
                onChange={(e) =>
                  setActiveRoles({ ...activeRoles, [role]: e.target.checked })
                }
                className="h-4.5 w-4.5 rounded border-slate-800 bg-slate-900 text-blue-600 focus:ring-0 cursor-pointer"
              />
              <span className="text-slate-350">{role}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Dropdown models */}
      <div className="space-y-3">
        <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Konfigurasi Model
        </span>
        <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
          {Object.entries(models).map(([agent, model]) => (
            <div key={agent} className="flex flex-col gap-1.5">
              <label className="text-[11px] text-slate-500 font-medium">{agent}</label>
              <select
                value={model}
                onChange={(e) => setModels({ ...models, [agent]: e.target.value })}
                className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white text-xs rounded-lg p-2.5 outline-none transition"
              >
                <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
                <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
                <option value="claude-opus-4-6">claude-opus-4-6</option>
              </select>
            </div>
          ))}
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition active:scale-95 shadow-md shadow-blue-900/30"
      >
        {saved ? (
          <>
            <Check className="h-4 w-4" />
            Tersimpan
          </>
        ) : (
          <>
            <Save className="h-4 w-4" />
            Simpan Konfigurasi
          </>
        )}
      </button>
    </div>
  );
}
