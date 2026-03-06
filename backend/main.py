from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncpg
import jwt
import bcrypt
import os
from datetime import datetime, timedelta, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr
import uuid

app = FastAPI(title="Rise Circle API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config
SECRET_KEY = os.getenv("JWT_SECRET", "rise-circle-secret-key-2024")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/risecircle")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7

security = HTTPBearer()
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)

@app.on_event("shutdown")
async def shutdown():
    await db_pool.close()

# ─── Auth Helpers ───────────────────────────────────────────────────────────

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return decode_token(credentials.credentials)

# ─── Models ─────────────────────────────────────────────────────────────────

class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    date: str
    is_study: bool = False
    instructions: Optional[str] = ""

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None

class HabitCreate(BaseModel):
    name: str
    target_frequency: str = "daily"

class AlarmCreate(BaseModel):
    alarm_time: str

class WakeConfirm(BaseModel):
    alarm_time: Optional[str] = None

class FocusSessionCreate(BaseModel):
    task_id: Optional[str] = None
    duration: int = 25

class FocusSessionEnd(BaseModel):
    session_id: str
    completed: bool = True

# ─── Auth Routes ────────────────────────────────────────────────────────────

@app.post("/auth/signup")
async def signup(req: SignUpRequest):
    pw_hash = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email=$1 OR username=$2", req.email, req.username)
        if existing:
            raise HTTPException(status_code=400, detail="Email or username already exists")
        user = await conn.fetchrow(
            "INSERT INTO users (username, email, password_hash) VALUES ($1,$2,$3) RETURNING id, username, email",
            req.username, req.email, pw_hash
        )
    token = create_token(str(user["id"]))
    return {"token": token, "user": {"id": str(user["id"]), "username": user["username"], "email": user["email"]}}

@app.post("/auth/login")
async def login(req: LoginRequest):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE email=$1", req.email)
    if not user or not bcrypt.checkpw(req.password.encode(), user["password_hash"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(str(user["id"]))
    return {"token": token, "user": {"id": str(user["id"]), "username": user["username"], "email": user["email"]}}

@app.get("/auth/me")
async def get_me(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, bio, streak_count, total_tasks_completed, productivity_score, join_date FROM users WHERE id=$1",
            uid
        )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(user)

# ─── Dashboard ──────────────────────────────────────────────────────────────

@app.get("/dashboard")
async def get_dashboard(uid: str = Depends(current_user)):
    today = date.today()
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT username, streak_count, total_tasks_completed, productivity_score FROM users WHERE id=$1", uid
        )
        today_tasks = await conn.fetch(
            "SELECT id, title, status, progress FROM tasks WHERE user_id=$1 AND date=$2", uid, today
        )
        wake = await conn.fetchrow(
            "SELECT wake_time, status, alarm_time FROM wake_records WHERE user_id=$1 AND date=$2", uid, today
        )
        focus_today = await conn.fetchrow(
            "SELECT COALESCE(SUM(duration),0) as total FROM focus_sessions WHERE user_id=$1 AND DATE(start_time)=$2",
            uid, today
        )
        leaderboard = await conn.fetch(
            "SELECT username, productivity_score, streak_count FROM users ORDER BY productivity_score DESC LIMIT 10"
        )
        habits = await conn.fetch(
            """SELECT h.id, h.name, h.streak,
               COALESCE(hl.completed, false) as done_today
               FROM habits h
               LEFT JOIN habit_logs hl ON hl.habit_id=h.id AND hl.date=$2
               WHERE h.user_id=$1""",
            uid, today
        )
        achievements = await conn.fetch(
            """SELECT a.title, a.icon, ua.date_earned
               FROM user_achievements ua JOIN achievements a ON a.id=ua.achievement_id
               WHERE ua.user_id=$1 ORDER BY ua.date_earned DESC LIMIT 5""",
            uid
        )

    tasks_list = [dict(t) for t in today_tasks]
    completed = sum(1 for t in tasks_list if t["status"] == "completed")
    total = len(tasks_list)

    return {
        "user": dict(user),
        "today": {
            "tasks": tasks_list,
            "tasks_completed": completed,
            "tasks_total": total,
            "completion_rate": round(completed / total * 100) if total > 0 else 0,
            "wake": dict(wake) if wake else None,
            "focus_minutes": focus_today["total"] if focus_today else 0,
        },
        "habits": [dict(h) for h in habits],
        "leaderboard": [dict(l) for l in leaderboard],
        "achievements": [dict(a) for a in achievements],
    }

# ─── Tasks ──────────────────────────────────────────────────────────────────

@app.get("/tasks")
async def get_tasks(month: Optional[str] = None, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        if month:
            tasks = await conn.fetch(
                "SELECT * FROM tasks WHERE user_id=$1 AND to_char(date,'YYYY-MM')=$2 ORDER BY date", uid, month
            )
        else:
            tasks = await conn.fetch("SELECT * FROM tasks WHERE user_id=$1 ORDER BY date DESC LIMIT 50", uid)
    return [dict(t) for t in tasks]

@app.post("/tasks")
async def create_task(req: TaskCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        task = await conn.fetchrow(
            "INSERT INTO tasks (user_id, title, description, date) VALUES ($1,$2,$3,$4) RETURNING *",
            uid, req.title, req.description, req.date
        )
        if req.is_study:
            await conn.execute(
                "INSERT INTO study_tasks (task_id, instructions) VALUES ($1,$2)",
                task["id"], req.instructions
            )
    return dict(task)

@app.patch("/tasks/{task_id}")
async def update_task(task_id: str, req: TaskUpdate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        task = await conn.fetchrow("SELECT * FROM tasks WHERE id=$1 AND user_id=$2", task_id, uid)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        updates = {k: v for k, v in req.dict().items() if v is not None}
        if not updates:
            return dict(task)
        set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        updated = await conn.fetchrow(
            f"UPDATE tasks SET {set_clause} WHERE id=$1 RETURNING *",
            task_id, *values
        )
        if req.status == "completed":
            await conn.execute(
                "UPDATE users SET total_tasks_completed=total_tasks_completed+1 WHERE id=$1", uid
            )
    return dict(updated)

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM tasks WHERE id=$1 AND user_id=$2", task_id, uid)
    return {"success": True}

# ─── Habits ─────────────────────────────────────────────────────────────────

@app.get("/habits")
async def get_habits(uid: str = Depends(current_user)):
    today = date.today()
    async with db_pool.acquire() as conn:
        habits = await conn.fetch(
            """SELECT h.*, COALESCE(hl.completed, false) as done_today
               FROM habits h
               LEFT JOIN habit_logs hl ON hl.habit_id=h.id AND hl.date=$2
               WHERE h.user_id=$1""",
            uid, today
        )
    return [dict(h) for h in habits]

@app.post("/habits")
async def create_habit(req: HabitCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        habit = await conn.fetchrow(
            "INSERT INTO habits (user_id, name, target_frequency) VALUES ($1,$2,$3) RETURNING *",
            uid, req.name, req.target_frequency
        )
    return dict(habit)

@app.post("/habits/{habit_id}/complete")
async def complete_habit(habit_id: str, uid: str = Depends(current_user)):
    today = date.today()
    async with db_pool.acquire() as conn:
        habit = await conn.fetchrow("SELECT * FROM habits WHERE id=$1 AND user_id=$2", habit_id, uid)
        if not habit:
            raise HTTPException(status_code=404, detail="Habit not found")
        await conn.execute(
            "INSERT INTO habit_logs (habit_id, date, completed) VALUES ($1,$2,true) ON CONFLICT (habit_id, date) DO UPDATE SET completed=true",
            habit_id, today
        )
        # Recalculate streak
        logs = await conn.fetch(
            "SELECT date FROM habit_logs WHERE habit_id=$1 AND completed=true ORDER BY date DESC LIMIT 60",
            habit_id
        )
        streak = 0
        check = today
        dates = {l["date"] for l in logs}
        while check in dates:
            streak += 1
            check -= timedelta(days=1)
        await conn.execute("UPDATE habits SET streak=$1 WHERE id=$2", streak, habit_id)
    return {"streak": streak}

@app.delete("/habits/{habit_id}")
async def delete_habit(habit_id: str, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM habits WHERE id=$1 AND user_id=$2", habit_id, uid)
    return {"success": True}

# ─── Alarm & Wake ────────────────────────────────────────────────────────────

@app.get("/alarm")
async def get_alarm(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        alarm = await conn.fetchrow("SELECT * FROM alarm_schedules WHERE user_id=$1", uid)
        today_wake = await conn.fetchrow(
            "SELECT * FROM wake_records WHERE user_id=$1 AND date=$2", uid, date.today()
        )
    return {"alarm": dict(alarm) if alarm else None, "today_wake": dict(today_wake) if today_wake else None}

@app.post("/alarm")
async def set_alarm(req: AlarmCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM alarm_schedules WHERE user_id=$1", uid)
        if existing:
            alarm = await conn.fetchrow(
                "UPDATE alarm_schedules SET alarm_time=$1, enabled=true WHERE user_id=$2 RETURNING *",
                req.alarm_time, uid
            )
        else:
            alarm = await conn.fetchrow(
                "INSERT INTO alarm_schedules (user_id, alarm_time) VALUES ($1,$2) RETURNING *",
                uid, req.alarm_time
            )
    return dict(alarm)

@app.post("/alarm/wake")
async def confirm_wake(req: WakeConfirm, uid: str = Depends(current_user)):
    today = date.today()
    now = datetime.now()
    async with db_pool.acquire() as conn:
        alarm = await conn.fetchrow("SELECT alarm_time FROM alarm_schedules WHERE user_id=$1", uid)
        alarm_time = alarm["alarm_time"] if alarm else None
        if alarm_time:
            alarm_dt = datetime.combine(today, alarm_time)
            diff = (now - alarm_dt).total_seconds() / 60
            status = "on_time" if diff <= 15 else "late"
        else:
            status = "on_time"
        record = await conn.fetchrow(
            """INSERT INTO wake_records (user_id, date, alarm_time, wake_time, status)
               VALUES ($1,$2,$3,$4,$5)
               ON CONFLICT (user_id, date) DO UPDATE SET wake_time=$4, status=$5
               RETURNING *""",
            uid, today, alarm_time, now, status
        )
        # Update streak
        if status == "on_time":
            await conn.execute(
                "UPDATE users SET streak_count=streak_count+1 WHERE id=$1", uid
            )
    return dict(record)

# ─── Focus Sessions ──────────────────────────────────────────────────────────

@app.post("/focus/start")
async def start_focus(req: FocusSessionCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "INSERT INTO focus_sessions (user_id, task_id, start_time, duration) VALUES ($1,$2,$3,$4) RETURNING *",
            uid, req.task_id, datetime.now(), req.duration
        )
    return dict(session)

@app.post("/focus/end")
async def end_focus(req: FocusSessionEnd, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "UPDATE focus_sessions SET end_time=$1, completed=$2 WHERE id=$3 AND user_id=$4 RETURNING *",
            datetime.now(), req.completed, req.session_id, uid
        )
    return dict(session) if session else {"error": "Session not found"}

@app.get("/focus/today")
async def get_focus_today(uid: str = Depends(current_user)):
    today = date.today()
    async with db_pool.acquire() as conn:
        sessions = await conn.fetch(
            "SELECT * FROM focus_sessions WHERE user_id=$1 AND DATE(start_time)=$2 ORDER BY start_time DESC",
            uid, today
        )
        total = await conn.fetchrow(
            "SELECT COALESCE(SUM(duration),0) as total FROM focus_sessions WHERE user_id=$1 AND DATE(start_time)=$2 AND completed=true",
            uid, today
        )
    return {"sessions": [dict(s) for s in sessions], "total_minutes": total["total"]}

# ─── Community / Messages ────────────────────────────────────────────────────

@app.get("/messages")
async def get_messages(room: str = "general", limit: int = 50, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        messages = await conn.fetch(
            """SELECT m.*, u.username, u.streak_count
               FROM messages m JOIN users u ON u.id=m.user_id
               WHERE m.room=$1 ORDER BY m.timestamp DESC LIMIT $2""",
            room, limit
        )
    return [dict(m) for m in reversed(messages)]

@app.post("/messages")
async def save_message(data: dict, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO messages (user_id, message, room) VALUES ($1,$2,$3)",
            uid, data.get("message",""), data.get("room","general")
        )
    return {"success": True}

# ─── Achievements ────────────────────────────────────────────────────────────

@app.get("/achievements")
async def get_achievements(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        all_achievements = await conn.fetch("SELECT * FROM achievements ORDER BY requirement_value")
        earned = await conn.fetch(
            "SELECT achievement_id FROM user_achievements WHERE user_id=$1", uid
        )
        earned_ids = {str(e["achievement_id"]) for e in earned}
    result = []
    for a in all_achievements:
        d = dict(a)
        d["earned"] = str(a["id"]) in earned_ids
        result.append(d)
    return result

# ─── Analytics ───────────────────────────────────────────────────────────────

@app.get("/analytics")
async def get_analytics(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        # Last 30 days task completion
        task_stats = await conn.fetch(
            """SELECT date, COUNT(*) as total,
               SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
               FROM tasks WHERE user_id=$1 AND date >= NOW()-INTERVAL '30 days'
               GROUP BY date ORDER BY date""",
            uid
        )
        # Wake times last 14 days
        wake_stats = await conn.fetch(
            "SELECT date, wake_time, status FROM wake_records WHERE user_id=$1 AND date >= NOW()-INTERVAL '14 days' ORDER BY date",
            uid
        )
        # Focus hours last 7 days
        focus_stats = await conn.fetch(
            """SELECT DATE(start_time) as day, SUM(duration) as minutes
               FROM focus_sessions WHERE user_id=$1 AND start_time >= NOW()-INTERVAL '7 days'
               AND completed=true GROUP BY day ORDER BY day""",
            uid
        )
        user = await conn.fetchrow(
            "SELECT streak_count, total_tasks_completed, productivity_score FROM users WHERE id=$1", uid
        )
    return {
        "task_stats": [dict(t) for t in task_stats],
        "wake_stats": [dict(w) for w in wake_stats],
        "focus_stats": [dict(f) for f in focus_stats],
        "summary": dict(user),
    }

# ─── Save Messages (for Node.js) ─────────────────────────────────────────────

class MessageCreate(BaseModel):
    message: str
    room: str = "general"

@app.post("/messages")
async def save_message(req: MessageCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO messages (user_id, message, room) VALUES ($1,$2,$3)",
            uid, req.message, req.room
        )
    return {"success": True}

# ─── Friend Groups ────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    description: str = ""

class GroupInvite(BaseModel):
    username: str

@app.get("/groups")
async def get_groups(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        groups = await conn.fetch(
            """SELECT g.*, gm.role,
               (SELECT COUNT(*) FROM group_members WHERE group_id=g.id) as member_count
               FROM groups g JOIN group_members gm ON gm.group_id=g.id
               WHERE gm.user_id=$1 ORDER BY g.created_at DESC""", uid
        )
    return [dict(g) for g in groups]

@app.post("/groups")
async def create_group(req: GroupCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        group = await conn.fetchrow(
            "INSERT INTO groups (name, description, owner_id) VALUES ($1,$2,$3) RETURNING *",
            req.name, req.description, uid
        )
        await conn.execute(
            "INSERT INTO group_members (group_id, user_id, role) VALUES ($1,$2,'owner')",
            group["id"], uid
        )
    return dict(group)

@app.post("/groups/{group_id}/invite")
async def invite_to_group(group_id: str, req: GroupInvite, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        target = await conn.fetchrow("SELECT id FROM users WHERE username=$1", req.username)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        existing = await conn.fetchrow(
            "SELECT id FROM group_members WHERE group_id=$1 AND user_id=$2", group_id, target["id"]
        )
        if existing:
            raise HTTPException(status_code=400, detail="Already a member")
        await conn.execute(
            "INSERT INTO group_members (group_id, user_id, role) VALUES ($1,$2,'member')",
            group_id, target["id"]
        )
    return {"success": True}

@app.get("/groups/{group_id}/members")
async def get_group_members(group_id: str, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        members = await conn.fetch(
            """SELECT u.id, u.username, u.streak_count, u.productivity_score,
               u.total_tasks_completed, gm.role, gm.joined_at
               FROM group_members gm JOIN users u ON u.id=gm.user_id
               WHERE gm.group_id=$1 ORDER BY u.productivity_score DESC""", group_id
        )
    return [dict(m) for m in members]

@app.delete("/groups/{group_id}/leave")
async def leave_group(group_id: str, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM group_members WHERE group_id=$1 AND user_id=$2", group_id, uid
        )
    return {"success": True}

# ─── Exercise ─────────────────────────────────────────────────────────────────

class WorkoutLogCreate(BaseModel):
    exercise_name: str
    sets: int = 0
    reps: int = 0
    duration_minutes: int = 0
    calories_burned: int = 0
    notes: str = ""

@app.get("/exercise/workouts")
async def get_workouts(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        logs = await conn.fetch(
            "SELECT * FROM workout_logs WHERE user_id=$1 ORDER BY logged_at DESC LIMIT 50", uid
        )
        today_stats = await conn.fetchrow(
            """SELECT COALESCE(SUM(calories_burned),0) as calories,
               COALESCE(SUM(duration_minutes),0) as minutes,
               COUNT(*) as exercises
               FROM workout_logs WHERE user_id=$1 AND DATE(logged_at)=$2""",
            uid, date.today()
        )
    return {"logs": [dict(l) for l in logs], "today": dict(today_stats)}

@app.post("/exercise/log")
async def log_workout(req: WorkoutLogCreate, uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        log = await conn.fetchrow(
            """INSERT INTO workout_logs
               (user_id, exercise_name, sets, reps, duration_minutes, calories_burned, notes)
               VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING *""",
            uid, req.exercise_name, req.sets, req.reps,
            req.duration_minutes, req.calories_burned, req.notes
        )
    return dict(log)

@app.get("/exercise/stats")
async def get_exercise_stats(uid: str = Depends(current_user)):
    async with db_pool.acquire() as conn:
        weekly = await conn.fetch(
            """SELECT DATE(logged_at) as day,
               SUM(calories_burned) as calories,
               SUM(duration_minutes) as minutes,
               COUNT(*) as exercises
               FROM workout_logs WHERE user_id=$1
               AND logged_at >= NOW()-INTERVAL '7 days'
               GROUP BY day ORDER BY day""", uid
        )
        total = await conn.fetchrow(
            """SELECT COALESCE(SUM(calories_burned),0) as total_calories,
               COALESCE(SUM(duration_minutes),0) as total_minutes,
               COUNT(*) as total_exercises
               FROM workout_logs WHERE user_id=$1""", uid
        )
    return {"weekly": [dict(w) for w in weekly], "total": dict(total)}
