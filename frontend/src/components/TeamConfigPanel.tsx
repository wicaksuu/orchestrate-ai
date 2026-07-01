import React, { useState, useEffect } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { Settings, Save, Check, ShieldCheck, ShieldAlert, KeyRound, Loader2 } from 'lucide-react';
import { AIProvider } from '../types';
import { api } from '../api';

export function TeamConfigPanel() {
  const { agentAISettings, teamConfig, updateAgentAISetting, updateConfig } = useSigmaStore();
  const [coderCount, setCoderCount] = useState(1);
  const [activeRoles, setActiveRoles] = useState<Record<string, boolean>>({});
  const [models, setModels] = useState<Record<string, string>>({});
  const [providers, setProviders] = useState<Record<string, AIProvider>>({});
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState(false);

  // Global Keys State
  const [globalAnthropicKey, setGlobalAnthropicKey] = useState('');
  const [globalOpenAIKey, setGlobalOpenAIKey] = useState('');
  const [globalGeminiKey, setGlobalGeminiKey] = useState('');

  // Validation States
  const [validationStatus, setValidationStatus] = useState<Record<string, { loading: boolean; valid?: boolean; message?: string }>>({
    anthropic: { loading: false },
    openai: { loading: false },
    gemini: { loading: false },
  });

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

  // Fungsi memvalidasi API Key secara real-time ke backend
  const handleValidateKey = async (provider: 'anthropic' | 'openai' | 'gemini') => {
    let key = '';
    if (provider === 'anthropic') key = globalAnthropicKey;
    else if (provider === 'openai') key = globalOpenAIKey;
    else if (provider === 'gemini') key = globalGeminiKey;

    if (!key.trim()) {
      setValidationStatus((prev) => ({
        ...prev,
        [provider]: { loading: false, valid: false, message: 'Masukkan API Key terlebih dahulu.' },
      }));
      return;
    }

    setValidationStatus((prev) => ({
      ...prev,
      [provider]: { loading: true },
    }));

    try {
      const res = await api.validateApiKey(provider, key);
      setValidationStatus((prev) => ({
        ...prev,
        [provider]: { loading: false, valid: res.valid, message: res.message },
      }));
    } catch (err: any) {
      setValidationStatus((prev) => ({
        ...prev,
        [provider]: { loading: false, valid: false, message: err.message },
      }));
    }
  };

  const handleSave = async () => {
    if (!teamConfig) return;
    const updated = {
      coder_count: coderCount,
      active_roles: activeRoles,
      models: models,
    };
    await updateConfig(updated);
    
    await Promise.all(
      Object.keys(models).map((agent) => {
        // Gunakan API Key global sebagai fallback jika individual key kosong
        let selectedKey = apiKeys[agent] || '';
        const selectedProvider = providers[agent] || 'gemini';
        
        if (!selectedKey) {
          if (selectedProvider === 'anthropic' && globalAnthropicKey) {
            selectedKey = globalAnthropicKey;
          } else if (selectedProvider === 'openai' && globalOpenAIKey) {
            selectedKey = globalOpenAIKey;
          } else if (selectedProvider === 'gemini' && globalGeminiKey) {
            selectedKey = globalGeminiKey;
          }
        }

        return updateAgentAISetting({
          agent_name: agent,
          provider: selectedProvider,
          model: models[agent],
          api_key: selectedKey || undefined,
        });
      })
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
    <div className="glass-panel p-6 rounded-xl flex flex-col h-full space-y-6 overflow-y-auto bg-slate-950/20">
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 shrink-0">
        <Settings className="h-5 w-5 text-blue-400" />
        <h3 className="font-semibold text-white">Konfigurasi Global & Tim</h3>
      </div>

      {/* SECTION 1: GLOBAL AI CONFIGURATION */}
      <div className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/10 p-4">
        <span className="block text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
          <KeyRound className="h-4 w-4" />
          Global AI Credentials
        </span>
        <p className="text-[11px] text-slate-400 leading-relaxed">
          Ketikkan API Key global di sini agar otomatis diwarisi oleh seluruh sub-agent pengembang.
        </p>

        {/* Google Gemini Global Key */}
        <div className="space-y-2">
          <label className="block text-[11px] text-slate-350 font-semibold">Google Gemini API Key (Tier Gratis)</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={globalGeminiKey}
              onChange={(e) => setGlobalGeminiKey(e.target.value)}
              placeholder="AIzaSy..."
              className="flex-1 bg-slate-950 border border-slate-850 hover:border-slate-750 text-white placeholder:text-slate-700 text-xs rounded-xl p-3 outline-none transition"
            />
            <button
              onClick={() => handleValidateKey('gemini')}
              disabled={validationStatus.gemini.loading}
              className="px-4 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold transition border border-slate-800 flex items-center gap-1.5 disabled:opacity-50 shrink-0"
            >
              {validationStatus.gemini.loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                'Uji Koneksi'
              )}
            </button>
          </div>
          {validationStatus.gemini.message && (
            <div className={`text-[10px] flex items-center gap-1 mt-1 font-semibold ${validationStatus.gemini.valid ? 'text-green-400' : 'text-rose-400'}`}>
              {validationStatus.gemini.valid ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              {validationStatus.gemini.message}
            </div>
          )}
        </div>

        {/* Anthropic Global Key */}
        <div className="space-y-2">
          <label className="block text-[11px] text-slate-350 font-semibold">Anthropic Claude API Key</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={globalAnthropicKey}
              onChange={(e) => setGlobalAnthropicKey(e.target.value)}
              placeholder="sk-ant-..."
              className="flex-1 bg-slate-950 border border-slate-850 hover:border-slate-750 text-white placeholder:text-slate-700 text-xs rounded-xl p-3 outline-none transition"
            />
            <button
              onClick={() => handleValidateKey('anthropic')}
              disabled={validationStatus.anthropic.loading}
              className="px-4 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold transition border border-slate-800 flex items-center gap-1.5 disabled:opacity-50 shrink-0"
            >
              {validationStatus.anthropic.loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                'Uji Koneksi'
              )}
            </button>
          </div>
          {validationStatus.anthropic.message && (
            <div className={`text-[10px] flex items-center gap-1 mt-1 font-semibold ${validationStatus.anthropic.valid ? 'text-green-400' : 'text-rose-400'}`}>
              {validationStatus.anthropic.valid ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              {validationStatus.anthropic.message}
            </div>
          )}
        </div>

        {/* OpenAI Global Key */}
        <div className="space-y-2">
          <label className="block text-[11px] text-slate-350 font-semibold">OpenAI API Key</label>
          <div className="flex gap-2">
            <input
              type="password"
              value={globalOpenAIKey}
              onChange={(e) => setGlobalOpenAIKey(e.target.value)}
              placeholder="sk-proj-..."
              className="flex-1 bg-slate-950 border border-slate-850 hover:border-slate-750 text-white placeholder:text-slate-700 text-xs rounded-xl p-3 outline-none transition"
            />
            <button
              onClick={() => handleValidateKey('openai')}
              disabled={validationStatus.openai.loading}
              className="px-4 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white rounded-xl text-xs font-semibold transition border border-slate-800 flex items-center gap-1.5 disabled:opacity-50 shrink-0"
            >
              {validationStatus.openai.loading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                'Uji Koneksi'
              )}
            </button>
          </div>
          {validationStatus.openai.message && (
            <div className={`text-[10px] flex items-center gap-1 mt-1 font-semibold ${validationStatus.openai.valid ? 'text-green-400' : 'text-rose-400'}`}>
              {validationStatus.openai.valid ? <ShieldCheck className="h-3.5 w-3.5" /> : <ShieldAlert className="h-3.5 w-3.5" />}
              {validationStatus.openai.message}
            </div>
          )}
        </div>
      </div>

      {/* SECTION 2: TIM CONFIGURATION */}
      <div className="space-y-5">
        <span className="block text-xs font-bold text-blue-400 uppercase tracking-wider">
          Konfigurasi Struktur Tim
        </span>

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
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(activeRoles).map(([role, active]) => (
              <label key={role} className="flex items-center gap-2.5 text-xs cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(e) =>
                    setActiveRoles({ ...activeRoles, [role]: e.target.checked })
                  }
                  className="h-4 w-4 rounded border-slate-800 bg-slate-900 text-blue-600 focus:ring-0 cursor-pointer"
                />
                <span className="text-slate-350">{role}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Agent mapping AI */}
        <div className="space-y-3">
          <span className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Model AI per Agent (Kustomisasi)
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-80 overflow-y-auto pr-1">
            {Object.entries(models).map(([agent, model]) => (
              <div key={agent} className="flex flex-col gap-2 rounded-xl border border-slate-850 bg-slate-950/40 p-3">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] text-slate-400 font-bold">{agent}</label>
                  {agentAISettings.find((item) => item.agent_name === agent)?.api_key_configured ? (
                    <span className="text-[9px] text-green-400 bg-green-500/10 border border-green-500/20 px-1.5 py-0.5 rounded font-mono">Key Tersimpan</span>
                  ) : (
                    <span className="text-[9px] text-slate-500 bg-slate-900/60 border border-slate-800 px-1.5 py-0.5 rounded font-mono">Gunakan Global</span>
                  )}
                </div>
                <select
                  value={providers[agent] || 'gemini'}
                  onChange={(e) => {
                    const provider = e.target.value as AIProvider;
                    const defaultModel =
                      provider === 'openai' || provider === 'codex'
                        ? 'gpt-5.5'
                        : provider === 'anthropic'
                          ? 'claude-sonnet-4-6'
                          : provider === 'gemini'
                            ? 'gemini-flash-latest'
                            : 'gemini-flash-latest';
                    setProviders({ ...providers, [agent]: provider });
                    setModels({ ...models, [agent]: defaultModel });
                  }}
                  className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white text-xs rounded-lg p-2 outline-none transition"
                >
                  <option value="openai">OpenAI</option>
                  <option value="codex">Codex (OpenAI)</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="gemini">Google Gemini</option>
                </select>
                <select
                  value={model}
                  onChange={(e) => setModels({ ...models, [agent]: e.target.value })}
                  className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white text-xs rounded-lg p-2 outline-none transition"
                >
                  {/* Google Gemini Flash Models */}
                  <option value="gemini-flash-latest">✦ Gemini 3.5 Flash (Latest)</option>
                  <option value="gemini-3.1-flash-lite">Gemini 3.1 Flash Lite</option>
                  <option value="gemini-3.0-flash">Gemini 3 Flash</option>
                  <option value="gemini-2.5-flash">Gemini 2.5 Flash</option>
                  <option value="gemini-2.5-flash-lite">Gemini 2.5 Flash Lite</option>
                  {/* OpenAI Models */}
                  <option value="gpt-5.5">gpt-5.5</option>
                  <option value="gpt-5">gpt-5</option>
                  {/* Anthropic Models */}
                  <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
                  <option value="claude-haiku-4-5-20251001">claude-haiku-4-5</option>
                  <option value="claude-opus-4-6">claude-opus-4-6</option>
                </select>
                <input
                  type="password"
                  value={apiKeys[agent] || ''}
                  onChange={(e) => setApiKeys({ ...apiKeys, [agent]: e.target.value })}
                  placeholder="Override API Key (Khusus Agent Ini)"
                  className="bg-slate-950 border border-slate-850 hover:border-slate-750 text-white placeholder:text-slate-700 text-[10px] rounded-lg p-2 outline-none transition"
                />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="shrink-0 pt-2 border-t border-slate-850">
        <button
          onClick={handleSave}
          className="w-full flex items-center justify-center gap-2 px-4 py-3.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-xl text-sm transition active:scale-95 shadow-lg shadow-blue-900/30"
        >
          {saved ? (
            <>
              <Check className="h-4.5 w-4.5 animate-pulse" />
              Konfigurasi Berhasil Disimpan
            </>
          ) : (
            <>
              <Save className="h-4.5 w-4.5" />
              Simpan & Terapkan Perubahan
            </>
          )}
        </button>
      </div>
    </div>
  );
}
