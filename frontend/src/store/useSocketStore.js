import { create } from 'zustand';

export const useSocketStore = create((set, get) => ({
  socket: null,
  isConnected: false,
  messages: [],
  notifications: [],

  connect: (url) => {
    if (get().socket) return;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        set({ isConnected: true });
        console.log('Successfully connected to WebSocket server');
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        // Handle different message types
        if (data.type === 'notification') {
          set((state) => ({ 
            notifications: [{
              id: Date.now(),
              type: data.level || data.severity || 'info',
              message: data.message || (typeof data.data === 'string' ? data.data : JSON.stringify(data.data)),
              raw: data,
            }, ...state.notifications].slice(0, 20)
          }));
        }
        
        set((state) => ({ 
          messages: [...state.messages, data].slice(-50) 
        }));
      };

      ws.onclose = () => {
        set({ isConnected: false, socket: null });
        console.log('WebSocket connection closed. Retrying in 5s...');
        setTimeout(() => get().connect(url), 5000);
      };

      ws.onerror = (err) => {
        console.error('WebSocket encountered error:', err);
        ws.close();
      };

      set({ socket: ws });
    } catch (error) {
      console.error('Failed to establish WebSocket connection:', error);
    }
  },

  disconnect: () => {
    const { socket } = get();
    if (socket) {
      socket.close();
      set({ socket: null, isConnected: false });
    }
  },

  sendMessage: (message) => {
    const { socket } = get();
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(message));
    }
  },

  clearNotifications: () => set({ notifications: [] }),
}));
