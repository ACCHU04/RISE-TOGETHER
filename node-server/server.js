const express = require("express");
const http = require("http");
const { Server } = require("socket.io");
const cors = require("cors");
const jwt = require("jsonwebtoken");
const axios = require("axios");

const app = express();
app.use(cors({ origin: "*" }));
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: { origin: "*", methods: ["GET", "POST"] },
});

const SECRET_KEY = process.env.JWT_SECRET || "rise-circle-secret-key-2024";
const PYTHON_API = process.env.PYTHON_API || "http://localhost:8000";
const PORT = process.env.PORT || 3000;

// Connected users map
const connectedUsers = new Map(); // socketId -> { userId, username }

// JWT middleware for socket
io.use((socket, next) => {
  const token = socket.handshake.auth.token;
  if (!token) return next(new Error("No token provided"));
  try {
    const payload = jwt.verify(token, SECRET_KEY);
    socket.userId = payload.sub;
    next();
  } catch (e) {
    next(new Error("Invalid token"));
  }
});

io.on("connection", async (socket) => {
  console.log(`User ${socket.userId} connected`);

  // Fetch username from Python API
  try {
    const res = await axios.get(`${PYTHON_API}/auth/me`, {
      headers: { Authorization: `Bearer ${socket.handshake.auth.token}` },
    });
    socket.username = res.data.username;
    socket.streak = res.data.streak_count;
  } catch (e) {
    socket.username = "User";
    socket.streak = 0;
  }

  connectedUsers.set(socket.id, {
    userId: socket.userId,
    username: socket.username,
    streak: socket.streak,
  });

  // Broadcast online users
  io.emit("online_users", Array.from(connectedUsers.values()));

  // Join room
  socket.on("join_room", (room) => {
    socket.join(room);
    socket.currentRoom = room;
    socket.to(room).emit("user_joined", {
      username: socket.username,
      room,
    });
  });

  // Chat message
  socket.on("send_message", async (data) => {
    const { message, room } = data;
    if (!message?.trim()) return;

    const msgData = {
      id: Date.now().toString(),
      user_id: socket.userId,
      username: socket.username,
      streak_count: socket.streak,
      message: message.trim(),
      timestamp: new Date().toISOString(),
      room: room || "general",
    };

    // Save to DB via Python API
    try {
      await axios.post(
        `${PYTHON_API}/messages`,
        { message: msgData.message, room: msgData.room },
        { headers: { Authorization: `Bearer ${socket.handshake.auth.token}` } }
      );
    } catch (e) {
      console.error("Failed to save message:", e.message);
    }

    io.to(room || "general").emit("new_message", msgData);
  });

  // Alarm wake broadcast
  socket.on("wake_confirmed", (data) => {
    io.emit("user_woke_up", {
      username: socket.username,
      time: data.time,
      streak: socket.streak,
    });
  });

  // Task completed broadcast
  socket.on("task_completed", (data) => {
    io.to("general").emit("activity_update", {
      type: "task",
      username: socket.username,
      text: `completed task: "${data.title}"`,
      timestamp: new Date().toISOString(),
    });
  });

  // Focus session broadcast
  socket.on("focus_started", (data) => {
    io.to("general").emit("activity_update", {
      type: "focus",
      username: socket.username,
      text: `started a ${data.duration}min focus session`,
      timestamp: new Date().toISOString(),
    });
  });

  // Typing indicator
  socket.on("typing", (room) => {
    socket.to(room).emit("user_typing", { username: socket.username });
  });

  socket.on("stop_typing", (room) => {
    socket.to(room).emit("user_stop_typing", { username: socket.username });
  });

  socket.on("disconnect", () => {
    connectedUsers.delete(socket.id);
    io.emit("online_users", Array.from(connectedUsers.values()));
    console.log(`User ${socket.userId} disconnected`);
  });
});

// REST endpoint to save messages (called by socket handler)
app.post("/save-message", async (req, res) => {
  res.json({ success: true });
});

// Health check
app.get("/health", (req, res) => res.json({ status: "ok", connected: connectedUsers.size }));

server.listen(PORT, () => {
  console.log(`Rise Circle Node.js server running on port ${PORT}`);
});
