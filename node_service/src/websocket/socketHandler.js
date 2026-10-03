const { Server } = require('socket.io');

const setupWebsocket = (server) => {
  const io = new Server(server, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    }
  });

  io.on('connection', (socket) => {
    console.log(`User connected: ${socket.id}`);

    // Join room for specific bot account updates
    socket.on('join_account', (accountId) => {
      socket.join(`account_${accountId}`);
      console.log(`User ${socket.id} joined room for account ${accountId}`);
    });

    // Handle bot status updates
    socket.on('bot_status', (data) => {
      io.to(`account_${data.accountId}`).emit('status_update', data);
    });

    // Handle real-time action feed
    socket.on('bot_action', (data) => {
      io.to(`account_${data.accountId}`).emit('action_feed', data);
    });

    socket.on('disconnect', () => {
      console.log(`User disconnected: ${socket.id}`);
    });
  });

  return io;
};

module.exports = setupWebsocket;
