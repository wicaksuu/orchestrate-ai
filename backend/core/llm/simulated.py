import asyncio
from typing import List, Dict
from core.llm.base import LLMProvider

class SimulatedLLMProvider(LLMProvider):
    """SimulatedLLMProvider digunakan untuk pengujian dan development offline."""
    async def complete(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4000,
    ) -> str:
        # Beri delay berpikir
        await asyncio.sleep(0.5)
        
        last_msg = messages[-1]["content"] if messages else ""
        last_msg_lower = last_msg.lower()

        # Logika dinamis simulasi LeadConsultant
        if "rekomendasikan tim" in last_msg_lower or "rekomendasi" in last_msg_lower:
            return "Berdasarkan analisis saya, tim optimal terdiri dari 1 Manager, 1 Coder, 1 Reviewer, dan 1 Tester. Silakan setujui komposisi ini untuk memulai fase eksekusi."
        elif "setuju" in last_msg_lower or "mulai" in last_msg_lower:
            return "Persetujuan diterima. Saya telah menginstruksikan Manager untuk memulai workflow pengembangan."
        
        return f"[Simulated Response] Saya telah memproses masukan Anda: '{last_msg}'."
