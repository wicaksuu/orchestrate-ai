import {
  AgentAISetting,
  AgentAISettingUpdate,
  AgentMessage,
  AgentState,
  TeamConfig,
  ProjectState,
  EscalationRequest,
  SigmaEvent,
  FileItem,
} from './types';

const API_BASE = '/api';

export const api = {
  async getProject(projectId: string): Promise<ProjectState> {
    const res = await fetch(`${API_BASE}/project?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat proyek');
    return res.json();
  },

  async getProjectList(): Promise<ProjectState[]> {
    const res = await fetch(`${API_BASE}/project/list`);
    if (!res.ok) throw new Error('Gagal memuat riwayat proyek');
    return res.json();
  },

  async createProject(name: string, description = '', externalPath = ''): Promise<ProjectState> {
    const res = await fetch(`${API_BASE}/project`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description, external_path: externalPath || null }),
    });
    if (!res.ok) throw new Error('Gagal membuat proyek');
    return res.json();
  },

  async updateProject(projectId: string, name: string, description = ''): Promise<ProjectState> {
    const res = await fetch(`${API_BASE}/project?project_id=${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, description }),
    });
    if (!res.ok) throw new Error('Gagal memperbarui proyek');
    return res.json();
  },

  async deleteProject(projectId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/project?project_id=${projectId}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Gagal menghapus proyek');
  },

  async getAgents(projectId?: string): Promise<AgentState[]> {
    const url = projectId ? `${API_BASE}/agents?project_id=${projectId}` : `${API_BASE}/agents`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Gagal memuat status agent');
    return res.json();
  },

  async getLogs(projectId: string): Promise<AgentMessage[]> {
    const res = await fetch(`${API_BASE}/logs?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat log komunikasi');
    return res.json();
  },

  async getEscalations(projectId: string): Promise<EscalationRequest[]> {
    const res = await fetch(`${API_BASE}/logs/escalation?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat data eskalasi');
    return res.json();
  },

  async sendChatMessage(projectId: string, content: string): Promise<{ status: string }> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, content }),
    });
    if (!res.ok) throw new Error('Gagal mengirim pesan');
    return res.json();
  },

  async resolveEscalation(projectId: string, escalationId: string, response: string): Promise<any> {
    const res = await fetch(`${API_BASE}/chat/escalation/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ project_id: projectId, escalation_id: escalationId, response }),
    });
    if (!res.ok) throw new Error('Gagal menyelesaikan eskalasi');
    return res.json();
  },

  async getTeamConfig(projectId: string): Promise<TeamConfig> {
    const res = await fetch(`${API_BASE}/config?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat konfigurasi');
    return res.json();
  },

  async saveTeamConfig(projectId: string, config: TeamConfig): Promise<any> {
    const res = await fetch(`${API_BASE}/config?project_id=${projectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Gagal menyimpan konfigurasi');
    return res.json();
  },

  async getAgentAISettings(projectId: string): Promise<AgentAISetting[]> {
    const res = await fetch(`${API_BASE}/config/agent-ai?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat konfigurasi AI agent');
    return res.json();
  },

  async saveAgentAISetting(
    projectId: string,
    setting: AgentAISettingUpdate,
  ): Promise<AgentAISetting> {
    const res = await fetch(`${API_BASE}/config/agent-ai?project_id=${projectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(setting),
    });
    if (!res.ok) throw new Error('Gagal menyimpan konfigurasi AI agent');
    return res.json();
  },

  async getEvents(projectId: string, limit = 50): Promise<SigmaEvent[]> {
    const res = await fetch(`${API_BASE}/events?project_id=${projectId}&limit=${limit}`);
    if (!res.ok) throw new Error('Gagal memuat event history');
    return res.json();
  },

  async validateApiKey(provider: string, apiKey: string): Promise<{ valid: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/config/validate-key`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, api_key: apiKey }),
    });
    if (!res.ok) throw new Error('Gagal memvalidasi API Key');
    return res.json();
  },

  async getProjectFiles(projectId: string): Promise<FileItem[]> {
    const res = await fetch(`${API_BASE}/project/files?project_id=${projectId}`);
    if (!res.ok) throw new Error('Gagal memuat daftar berkas');
    return res.json();
  },
};
