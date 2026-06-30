import React, { useState, useEffect } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { Settings, Save, Check } from 'lucide-react';
import { AIProvider } from '../types';

export function TeamConfigPanel() {
  const { agentAISettings, teamConfig, updateAgentAISetting, updateConfig } = useSigmaStore();
  const [coderCount, setCoderCount] = useState(1);
  const [activeRoles, setActiveRoles] = useState<Record<string, boolean>>({});
  const [models, setModels] = useState<Record<string, string>>({});
  const [providers, setProviders] = useState<Record<string, AIProvider>>({});
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (teamConfig) {
      setCoderCount(teamConfig.coder_count);
      setActiveRoles(teamConfig.active_roles);
      setModels(teamConfig.models);
    }
  }, [teamConfig]);

  useEffect(() => {
    const nextProviders: Record<string, AIProvider> = {};
    const nextModels: Record<string, string> = {};
    for (const item of agentAISettings) {
      nextProviders[item.agent_name] = item.provider;
      nextModels[item.agent_name] = item.model;
    }
    setProviders(nextProviders);
    setModels((current) => ({ ...current, ...nextModels }));
  }, [agentAISettings]);

  const handleSave = async () => {
    if (!teamConfig) return;
    const updated = {
      coder_count: coderCount,
      active_roles: activeRoles,
      models: models,
    };
    await updateConfig(updated);
    await Promise.all(
      Object.keys(models).map((agent) =>
        updateAgentAISetting({
          agent_name: agent,
          provider: providers[agent] || 'simulated',
          model: models[agent],
          api_key: apiKeys[agent] || undefined,
        })
      )
    );
    setApiKeys({});
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

      {/* Provider and model config */}
      <div className="space-y-3">
        <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
          AI Provider per Agent
        </span>
        <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
          {Object.entries(models).map(([agent, model]) => (
            <div key={agent} className="flex flex-col gap-2 rounded-lg border border-slate-850 bg-slate-950/50 p-3">
              <div className="flex items-center justify-between">
                <label className="text-[11px] text-slate-400 font-semibold">{agent}</label>
                {agentAISettings.find((item) => item.agent_name === agent)?.api_key_configured ? (
                  <span className="text-[10px] text-emerald-400">API key tersimpan</span>
                ) : (
                  <span className="text-[10px] text-slate-600">belum ada key</span>
                )}
              </div>
              <select
                value={providers[agent] || 'simulated'}
                onChange={(e) => {
                  const provider = e.target.value as AIProvider;
                  const defaultModel =
                    provider === 'openai' || provider === 'codex'
                      ? 'gpt-5.5'
                      : provider === 'anthropic'
                        ? 'claude-sonnet-4-6'
                        : 'simulated';
                  setProviders({ ...providers, [agent]: provider });
                  setModels({ ...models, [agent]: defaultModel });
                }}
                className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white text-xs rounded-lg p-2.5 outline-none transition"
              >
                <option value="simulated">Simulated</option>
                <option value="openai">OpenAI</option>
                <option value="codex">Codex (OpenAI)</option>
                <option value="anthropic">Anthropic</option>
              </select>
              <select
                value={model}
                onChange={(e) => setModels({ ...models, [agent]: e.target.value })}
                className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white text-xs rounded-lg p-2.5 outline-none transition"
              >
                <option value="simulated">simulated</option>
                <option value="gpt-5.5">gpt-5.5</option>
                <option value="gpt-5">gpt-5</option>
                <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
                <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
                <option value="claude-opus-4-6">claude-opus-4-6</option>
              </select>
              <input
                type="password"
                value={apiKeys[agent] || ''}
                onChange={(e) => setApiKeys({ ...apiKeys, [agent]: e.target.value })}
                placeholder="API token baru (kosongkan untuk mempertahankan)"
                className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white placeholder:text-slate-650 text-xs rounded-lg p-2.5 outline-none transition"
              />
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
