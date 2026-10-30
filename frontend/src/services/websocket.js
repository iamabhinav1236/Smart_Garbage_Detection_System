import { withToken } from './api';

class WebSocketService {
  constructor() {
    this.ws = null;
    this.subscribers = new Set();
    this.reconnectTimer = null;
    this.isConnected = false;
  }

  connect() {
    if (!localStorage.getItem('token')) return; // live telemetry requires login
    const wsUrl = withToken((location.protocol === 'https:' ? 'wss://' : 'ws://') + (window.location.hostname || 'localhost') + ':8000/ws/live');

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        console.log('[WS] Connected to Smart Garbage Telemetry Stream');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.subscribers.forEach((callback) => callback(data));
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };

      this.ws.onclose = (event) => {
        this.isConnected = false;
        if (event.code === 1008) return; // rejected: not logged in
        console.warn('[WS] Stream closed. Retrying in 3 seconds...');
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.error('[WS] Error:', err);
        this.ws.close();
      };
    } catch (err) {
      console.error('[WS] Connection exception:', err);
      this.scheduleReconnect();
    }
  }

  scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => this.connect(), 3000);
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  disconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.ws) {
      this.ws.onclose = null; // intentional close: don't auto-reconnect
      this.ws.close();
    }
  }
}

export const wsService = new WebSocketService();
