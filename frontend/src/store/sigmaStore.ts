import { create } from 'zustand';
import { api } from '../api';
import {
  AgentAISetting,
  AgentAISettingUpdate,
  AgentMessage,
  AgentState,
  TeamConfig,
  ProjectState,
  EscalationRequest,
  SigmaEvent,
} from '../types';

interface SigmaState {
  project: ProjectState | null;
  agents: AgentState[];
  messages: AgentMessage[];
  escalations: EscalationRequest[];
  teamConfig: TeamConfig | null;
  agentAISettings: AgentAISetting[];
  events: SigmaEvent[];
  loading: boolean;
  error: string | null;

  // Actions
  initProject: (name: string, description?: string) => Promise<void>;
  loadProject: (projectId: string) => Promise<void>;
  loadAgents: () => Promise<void>;
  loadLogs: () => Promise<void>;
  loadConfig: () => Promise<void>;
  loadAgentAISettings: () => Promise<void>;
  loadEvents: () => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  resolveEscalation: (escalationId: string, response: string) => Promise<void>;
  updateConfig: (config: TeamConfig) => Promise<void>;
  updateAgentAISetting: (setting: AgentAISettingUpdate) => Promise<void>;
  
  // Real-time updates handlers
  handleAgentStatusUpdate: (updatedAgent: AgentState) => void;
  handleNewMessage: (msg: AgentMessage) => void;
  handleNewEscalation: (esc: EscalationRequest) => void;
  handleEscalationResolved: (escalationId: string) => void;
  handleNewEvent: (event: SigmaEvent) => void;
}

export const useSigmaStore = create<SigmaState>((set: any, get: any) => ({
  project: null,
  agents: [],
  messages: [],
  escalations: [],
  teamConfig: null,
  agentAISettings: [],
  events: [],
  loading: false,
  error: null,

  initProject: async (name: string, description = '') => {
    set({ loading: true, error: null, messages: [], escalations: [], agents: [], events: [], agentAISettings: [] });
    try {
      const project = await api.createProject(name, description);
      set({ project, loading: false });
      // Load initial data
      await get().loadAgents();
      await get().loadLogs();
      await get().loadConfig();
      await get().loadAgentAISettings();
      await get().loadEvents();
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  loadProject: async (projectId: string) => {
    set({ loading: true, error: null, messages: [], escalations: [], agents: [], events: [], agentAISettings: [] });
    try {
      const project = await api.getProject(projectId);
      set({ project, loading: false });
      await get().loadAgents();
      await get().loadLogs();
      await get().loadConfig();
      await get().loadAgentAISettings();
      await get().loadEvents();
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  loadAgents: async () => {
    const { project } = get();
    try {
      const agents = await api.getAgents(project?.project_id);
      set({ agents });
    } catch (err: any) {
      logger.error('Gagal load agents', err);
    }
  },

  loadLogs: async () => {
    const { project } = get();
    if (!project) return;
    try {
      const messages = await api.getLogs(project.project_id);
      const escalations = await api.getEscalations(project.project_id);
      set({ messages, escalations: escalations.filter(e => !e.resolved) });
    } catch (err: any) {
      logger.error('Gagal load logs', err);
    }
  },

  loadConfig: async () => {
    const { project } = get();
    if (!project) return;
    try {
      const teamConfig = await api.getTeamConfig(project.project_id);
      set({ teamConfig });
    } catch (err: any) {
      logger.error('Gagal load team config', err);
    }
  },

  loadAgentAISettings: async () => {
    const { project } = get();
    if (!project) return;
    try {
      const agentAISettings = await api.getAgentAISettings(project.project_id);
      set({ agentAISettings });
    } catch (err: any) {
      logger.error('Gagal load agent AI settings', err);
    }
  },

  loadEvents: async () => {
    const { project } = get();
    if (!project) return;
    try {
      const events = await api.getEvents(project.project_id);
      set({ events });
    } catch (err: any) {
      logger.error('Gagal load events', err);
    }
  },

  sendMessage: async (content: string) => {
    const { project } = get();
    if (!project) return;
    try {
      await api.sendChatMessage(project.project_id, content);
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  resolveEscalation: async (escalationId: string, response: string) => {
    const { project } = get();
    if (!project) return;
    try {
      await api.resolveEscalation(project.project_id, escalationId, response);
      set((state: SigmaState) => ({
        escalations: state.escalations.filter((e: EscalationRequest) => e.id !== escalationId),
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updateConfig: async (config: TeamConfig) => {
    const { project } = get();
    if (!project) return;
    try {
      await api.saveTeamConfig(project.project_id, config);
      set({ teamConfig: config });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  updateAgentAISetting: async (setting: AgentAISettingUpdate) => {
    const { project } = get();
    if (!project) return;
    try {
      const saved = await api.saveAgentAISetting(project.project_id, setting);
      set((state: SigmaState) => ({
        agentAISettings: [
          ...state.agentAISettings.filter((item) => item.agent_name !== saved.agent_name),
          saved,
        ],
      }));
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  handleAgentStatusUpdate: (updatedAgent: AgentState) => {
    set((state: SigmaState) => ({
      agents: state.agents.map((a: AgentState) =>
        a.name === updatedAgent.name ? updatedAgent : a
      ),
    }));
  },

  handleNewMessage: (msg: AgentMessage) => {
    set((state: SigmaState) => {
      // Cegah duplikasi pesan
      if (state.messages.some((m: AgentMessage) => m.id === msg.id)) return state;
      return { messages: [...state.messages, msg] };
    });
  },

  handleNewEscalation: (esc: EscalationRequest) => {
    set((state: SigmaState) => {
      if (state.escalations.some((e: EscalationRequest) => e.id === esc.id)) return state;
      return { escalations: [...state.escalations, esc] };
    });
  },

  handleEscalationResolved: (escalationId: string) => {
    set((state: SigmaState) => ({
      escalations: state.escalations.filter((e: EscalationRequest) => e.id !== escalationId),
    }));
  },

  handleNewEvent: (event: SigmaEvent) => {
    set((state: SigmaState) => {
      // Deduplikasi
      if (state.events.some((e: SigmaEvent) => e.event_id === event.event_id)) return state;
      
      const nextEvents = [...state.events, event];
      
      // Update status proyek jika menerima event project_status
      if (event.event_type === 'project_status' && state.project && event.payload && event.payload.status) {
        return {
          events: nextEvents,
          project: {
            ...state.project,
            status: event.payload.status
          }
        };
      }
      
      return { events: nextEvents };
    });
  }
}));

const logger = {
  error: (msg: string, err: any) => console.error(msg, err),
};
