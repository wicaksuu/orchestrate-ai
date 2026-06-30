export type AgentName =
  | 'LeadConsultant'
  | 'Manager'
  | 'PromptEngineer'
  | 'Coder'
  | 'Reviewer'
  | 'Tester'
  | 'Integrator';

export type AgentStatus =
  | 'IDLE'
  | 'THINKING'
  | 'WORKING'
  | 'WAITING_REVIEW'
  | 'WAITING_USER_INPUT'
  | 'DONE'
  | 'BLOCKED'
  | 'ERROR';

export type MessageType = 'user' | 'agent_comm' | 'system' | 'log';
export type MessagePriority = 'low' | 'medium' | 'high' | 'critical';

export interface MessageMetadata {
  sender: string;
  receiver: string;
  step_id?: string;
  token_estimate?: number;
  timestamp: string;
}

export interface AgentMessage {
  id: string;
  project_id: string;
  message_type: MessageType;
  content: string;
  priority: MessagePriority;
  metadata: MessageMetadata;
  timestamp: string;
}

export interface AgentState {
  name: AgentName;
  status: AgentStatus;
  last_message?: string;
  token_count: number;
  updated_at: string;
}

export interface TeamConfig {
  coder_count: number;
  active_roles: Record<string, boolean>;
  models: Record<string, string>;
}

export interface ProjectState {
  project_id: string;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface EscalationRequest {
  id: string;
  project_id: string;
  agent_name: AgentName;
  description: string;
  options?: string[];
  timeout_seconds?: number;
  created_at: string;
  resolved: boolean;
  response?: string;
}

export interface SigmaEvent {
  event_id: string;
  project_id: string;
  event_type: string;
  payload: any;
  timestamp: string;
}
