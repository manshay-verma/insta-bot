const express = require('express');
const cors = require('cors');
const http = require('http');
const dotenv = require('dotenv');
const connectDB = require('./config/db');
const setupWebsocket = require('./websocket/socketHandler');

dotenv.config();

// Initialize Express app
const app = express();
const server = http.createServer(app);

// Connect to MongoDB
connectDB();

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', message: 'Node Service is running.' });
});

// Setup WebSockets
const io = setupWebsocket(server);
app.set('socketio', io);

// Start server
const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`Node Service running on port ${PORT}`);
});
