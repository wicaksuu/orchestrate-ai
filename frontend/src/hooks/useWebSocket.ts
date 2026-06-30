import { useEffect, useRef } from 'react';
import { useSigmaStore } from '../store/sigmaStore';
import { SigmaEvent } from '../types';

export function useWebSocket(projectId: string | undefined) {
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);

  const {
    handleAgentStatusUpdate,
    handleNewMessage,
    handleNewEscalation,
    handleEscalationResolved,
    handleNewEvent,
    loadAgents,
  } = useSigmaStore();

  useEffect(() => {
    if (!projectId) return;

    function connect() {
      // Tentukan URL WebSocket (gunakan schema ws:// atau wss:// berdasarkan protocol halaman)
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      const wsUrl = `${protocol}//${host}/ws?project_id=${projectId}`;

      console.log(`Menghubungkan WebSocket ke: ${wsUrl}`);
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('WebSocket terhubung.');
        // Refresh status agent saat baru terhubung
        loadAgents();
      };

      socket.onmessage = (event) => {
        try {
          const sigmaEvent: SigmaEvent = JSON.parse(event.data);
          const { event_type, payload } = sigmaEvent;

          console.log(`WebSocket event diterima: ${event_type}`, payload);

          // Panggil handler event global
          handleNewEvent(sigmaEvent);

          switch (event_type) {
            case 'agent_status':
              handleAgentStatusUpdate(payload);
              break;
            case 'message':
              handleNewMessage(payload);
              break;
            case 'escalation':
              handleNewEscalation(payload);
              break;
            case 'escalation_resolved':
              handleEscalationResolved(payload.escalation_id);
              break;
            case 'config_changed':
              useSigmaStore.setState({ teamConfig: payload });
              break;
            default:
              break;
          }
        } catch (err) {
          console.error('Gagal memproses WebSocket message:', err);
        }
      };

      socket.onclose = (e) => {
        console.log(`WebSocket ditutup: ${e.reason}. Mencoba menghubungkan kembali dalam 3 detik...`);
        reconnectTimeoutRef.current = window.setTimeout(() => {
          connect();
        }, 3000);
      };

      socket.onerror = (err) => {
        console.error('WebSocket error:', err);
        socket.close();
      };
    }

    connect();

    return () => {
      if (socketRef.current) {
        // Hapus onclose agar tidak memicu auto reconnect saat cleanup
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [projectId]);

  return socketRef.current;
}
