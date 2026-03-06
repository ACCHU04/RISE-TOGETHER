# ⚡ Rise Circle

> A full-stack discipline and productivity platform — track habits, focus sessions, wake-up times, and compete with your community.

---

## 🚀 Quick Start

### Option A: Docker (Recommended)

```bash
git clone <repo>
cd rise-circle
docker-compose up --build
```

Then open `index.html` in your browser (or serve with any static file server).

---

### Option B: Manual Setup

#### 1. PostgreSQL

```bash
# Create database
psql -U postgres -c "CREATE DATABASE risecircle;"
psql -U postgres -d risecircle -f backend/schema.sql
```

#### 2. Python FastAPI Backend

```bash
cd backend
pip install -r requirements.txt
DATABASE_URL=postgresql://postgres:password@localhost:5432/risecircle \
JWT_SECRET=your-secret-key \
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

#### 3. Node.js Real-time Server

```bash
cd node-server
npm install
PYTHON_API=http://localhost:8000 \
JWT_SECRET=your-secret-key \
node server.js
```

#### 4. Frontend

Serve the project root with any HTTP server:

```bash
# Python
python -m http.server 5500

# Node
npx serve .

# VS Code Live Server extension
```

Open: http://localhost:5500

---

## 📁 Project Structure

```
rise-circle/
├── index.html                   ← Root redirect
├── docker-compose.yml
│
├── backend/                     ← Python FastAPI
│   ├── main.py                  ← All API routes
│   ├── schema.sql               ← PostgreSQL schema + seed data
│   ├── requirements.txt
│   └── Dockerfile
│
├── node-server/                 ← Node.js + Socket.IO
│   ├── server.js                ← Real-time chat & events
│   ├── package.json
│   └── Dockerfile
│
└── frontend/
    ├── css/
    │   └── styles.css           ← Global design system
    ├── js/
    │   └── app.js               ← API client, auth, utilities
    └── pages/
        ├── login.html           ← Auth (login + signup)
        ├── dashboard.html       ← Main dashboard
        ├── tasks.html           ← Calendar task manager
        ├── focus.html           ← Pomodoro timer
        ├── alarm.html           ← Wake alarm system
        ├── habits.html          ← Habit tracker with streaks
        ├── community.html       ← Real-time chat
        ├── achievements.html    ← Badge system
        └── analytics.html      ← Productivity charts
```

---

## 🔌 API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Create account |
| POST | `/auth/login` | Login → JWT token |
| GET | `/auth/me` | Current user info |
| GET | `/dashboard` | Full dashboard data |
| GET | `/tasks?month=YYYY-MM` | Get tasks by month |
| POST | `/tasks` | Create task |
| PATCH | `/tasks/{id}` | Update task |
| DELETE | `/tasks/{id}` | Delete task |
| GET | `/habits` | Get habits with today's status |
| POST | `/habits` | Create habit |
| POST | `/habits/{id}/complete` | Log habit completion |
| DELETE | `/habits/{id}` | Delete habit |
| GET | `/alarm` | Get alarm settings + today's wake |
| POST | `/alarm` | Set alarm time |
| POST | `/alarm/wake` | Confirm wake-up |
| POST | `/focus/start` | Start focus session |
| POST | `/focus/end` | End focus session |
| GET | `/focus/today` | Today's focus stats |
| GET | `/messages?room=general` | Chat message history |
| GET | `/achievements` | All badges + earned status |
| GET | `/analytics` | Full analytics data |

---

## 🔄 Socket.IO Events

**Client → Server:**
| Event | Payload | Description |
|-------|---------|-------------|
| `join_room` | `roomName` | Join chat room |
| `send_message` | `{message, room}` | Send chat message |
| `wake_confirmed` | `{time}` | Broadcast wake up |
| `task_completed` | `{title}` | Broadcast task done |
| `focus_started` | `{duration}` | Broadcast focus start |
| `typing` | `room` | Typing indicator |
| `stop_typing` | `room` | Stop typing indicator |

**Server → Client:**
| Event | Description |
|-------|-------------|
| `new_message` | New chat message |
| `online_users` | Updated online user list |
| `user_joined` | User joined room |
| `user_woke_up` | Someone confirmed wake |
| `activity_update` | Task/focus activity feed |
| `user_typing` | Typing indicator |

---

## 🗃️ Database Tables

- `users` — accounts + stats
- `tasks` — calendar tasks
- `study_tasks` — study task details
- `habits` — habit definitions + streaks
- `habit_logs` — daily habit completion
- `alarm_schedules` — user alarm settings
- `wake_records` — wake time history
- `focus_sessions` — Pomodoro sessions
- `messages` — chat history
- `achievements` — badge definitions
- `user_achievements` — earned badges

---

## 🎨 Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS |
| Design | CSS Variables, Syne + DM Sans fonts |
| Backend API | Python FastAPI + asyncpg |
| Real-time | Node.js + Socket.IO |
| Database | PostgreSQL |
| Auth | JWT (HS256) |
| Passwords | bcrypt |
| Deployment | Docker + docker-compose |

---

## 🔐 Security

- Passwords hashed with `bcrypt`
- JWT authentication on all protected routes
- CORS configured (tighten for production)
- SQL injection safe via parameterized queries
- Rate limiting recommended for production

---

## 🚧 Production Checklist

- [ ] Change `JWT_SECRET` to a strong random key
- [ ] Set `CORS` origin to your actual domain
- [ ] Add HTTPS (nginx + certbot)
- [ ] Set up Redis for session caching
- [ ] Add rate limiting middleware
- [ ] Configure PostgreSQL connection pooling
- [ ] Set up backup strategy for PostgreSQL

---

## 📈 Future Enhancements

- Mobile app (React Native / Flutter)
- AI Study Assistant (OpenAI integration)
- Weekly productivity email reports
- Smart notifications (push)
- Study resource sharing
- Accountability groups
- Mood tracking
- Dark/light mode toggle

---

Built with ⚡ by Rise Circle
