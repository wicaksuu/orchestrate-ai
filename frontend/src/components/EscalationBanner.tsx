import React, { useState } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { AlertTriangle, Send } from 'lucide-react';

export function EscalationBanner() {
  const { escalations, resolveEscalation } = useSigmaStore();
  const [inputText, setInputText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (escalations.length === 0) return null;

  const currentEscalation = escalations[0]; // tampilkan satu per satu

  const handleResolve = async (val: string) => {
    setSubmitting(true);
    try {
      await resolveEscalation(currentEscalation.id, val);
      setInputText('');
    } catch (e) {
      console.error(e);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-gradient-to-r from-amber-600 to-orange-600 border-b border-orange-500 text-white px-6 py-4 flex flex-col md:flex-row items-center justify-between gap-4 animate-bounce shadow-lg relative z-50">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-orange-700/50 rounded-lg">
          <AlertTriangle className="h-6 w-6 animate-pulse" />
        </div>
        <div>
          <h4 className="font-semibold text-lg">Input Pengguna Diperlukan — Eskalasi dari {currentEscalation.agent_name}</h4>
          <p className="text-sm text-orange-100">{currentEscalation.description}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
        {currentEscalation.options && currentEscalation.options.map((opt) => (
          <button
            key={opt}
            onClick={() => handleResolve(opt)}
            disabled={submitting}
            className="px-4 py-2 bg-white text-orange-700 hover:bg-orange-50 rounded-lg text-sm font-semibold transition shadow-md active:scale-95 disabled:opacity-50"
          >
            {opt}
          </button>
        ))}

        <div className="flex items-center bg-orange-700/30 border border-orange-400/50 rounded-lg overflow-hidden w-full md:w-80">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ketik jawaban khusus..."
            className="bg-transparent px-3 py-2 text-sm text-white placeholder-orange-200 outline-none w-full"
            onKeyDown={(e) => e.key === 'Enter' && inputText.trim() && handleResolve(inputText)}
          />
          <button
            onClick={() => inputText.trim() && handleResolve(inputText)}
            disabled={submitting || !inputText.trim()}
            className="p-2 text-white hover:bg-orange-600 transition disabled:opacity-30"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
