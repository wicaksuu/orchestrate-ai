import { describe, it, expect, beforeEach } from 'vitest';
import { useSigmaStore } from './sigmaStore';
import { ProjectState, SigmaEvent } from '../types';

describe('Zustand store (sigmaStore) Event Handling', () => {
  beforeEach(() => {
    // Reset state store secara manual sebelum setiap test
    useSigmaStore.setState({
      project: null,
      agents: [],
      messages: [],
      escalations: [],
      events: [],
      loading: false,
      error: null,
    });
  });

  it('harus memperbarui project.status ketika menerima event project_status', () => {
    const dummyProject: ProjectState = {
      project_id: 'p123',
      name: 'Test Project',
      status: 'approved',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    useSigmaStore.setState({ project: dummyProject });

    const statusEvent: SigmaEvent = {
      event_id: 'event-01',
      project_id: 'p123',
      event_type: 'project_status',
      payload: { status: 'running' },
      timestamp: new Date().toISOString(),
    };

    useSigmaStore.getState().handleNewEvent(statusEvent);

    const updatedProject = useSigmaStore.getState().project;
    expect(updatedProject).not.toBeNull();
    expect(updatedProject?.status).toBe('running');
    expect(useSigmaStore.getState().events).toHaveLength(1);
  });

  it('tidak boleh menambahkan event dengan ID yang sama (deduplikasi)', () => {
    const dummyProject: ProjectState = {
      project_id: 'p123',
      name: 'Test Project',
      status: 'approved',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    useSigmaStore.setState({ project: dummyProject });

    const event1: SigmaEvent = {
      event_id: 'duplicate-id',
      project_id: 'p123',
      event_type: 'project_status',
      payload: { status: 'running' },
      timestamp: new Date().toISOString(),
    };

    const event2: SigmaEvent = {
      event_id: 'duplicate-id',
      project_id: 'p123',
      event_type: 'project_status',
      payload: { status: 'completed' },
      timestamp: new Date().toISOString(),
    };

    useSigmaStore.getState().handleNewEvent(event1);
    useSigmaStore.getState().handleNewEvent(event2); // ID sama, harus di-ignore

    expect(useSigmaStore.getState().events).toHaveLength(1);
    expect(useSigmaStore.getState().project?.status).toBe('running');
  });
});
