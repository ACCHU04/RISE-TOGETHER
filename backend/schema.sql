-- Rise Circle Database Schema

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    profile_picture TEXT DEFAULT NULL,
    bio TEXT DEFAULT '',
    join_date TIMESTAMP DEFAULT NOW(),
    streak_count INT DEFAULT 0,
    total_tasks_completed INT DEFAULT 0,
    productivity_score FLOAT DEFAULT 0
);

-- Tasks
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    date DATE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed
    progress INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Study Tasks
CREATE TABLE study_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    instructions TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    progress INT DEFAULT 0
);

-- Habits
CREATE TABLE habits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    target_frequency VARCHAR(50) DEFAULT 'daily',
    streak INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Habit Logs
CREATE TABLE habit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    habit_id UUID REFERENCES habits(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    UNIQUE(habit_id, date)
);

-- Alarm Schedules
CREATE TABLE alarm_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    alarm_time TIME NOT NULL,
    enabled BOOLEAN DEFAULT TRUE
);

-- Wake Records
CREATE TABLE wake_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    alarm_time TIME,
    wake_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'pending',  -- on_time, late, missed
    UNIQUE(user_id, date)
);

-- Focus Sessions
CREATE TABLE focus_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration INT DEFAULT 0,  -- in minutes
    completed BOOLEAN DEFAULT FALSE
);

-- Chat Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    room VARCHAR(100) DEFAULT 'general'
);

-- Achievements
CREATE TABLE achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(10),
    requirement_type VARCHAR(50),  -- wake_streak, tasks_completed, focus_hours, habit_streak
    requirement_value INT
);

-- User Achievements
CREATE TABLE user_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    achievement_id UUID REFERENCES achievements(id) ON DELETE CASCADE,
    date_earned TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, achievement_id)
);

-- Seed Achievements
INSERT INTO achievements (title, description, icon, requirement_type, requirement_value) VALUES
('Early Bird', 'Wake before 6 AM for 7 days', '🏅', 'wake_streak', 7),
('Study Master', 'Complete 50 study tasks', '📚', 'tasks_completed', 50),
('Consistency King', 'Maintain a 30 day streak', '👑', 'habit_streak', 30),
('Focus Champion', 'Complete 20 focus sessions', '🎯', 'focus_sessions', 20),
('Rise Warrior', 'Wake up on time 14 days in a row', '⚔️', 'wake_streak', 14),
('Task Hero', 'Complete 100 tasks total', '🦸', 'tasks_completed', 100),
('Night Owl Reformed', 'Wake before 5 AM once', '🦉', 'early_wake', 1),
('Habit Builder', 'Track a habit for 10 days', '🔥', 'habit_streak', 10);

-- Friend Groups
CREATE TABLE IF NOT EXISTS groups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT DEFAULT '',
    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS group_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member',
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);

-- Exercise / Workout Logs
CREATE TABLE IF NOT EXISTS workout_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    exercise_name VARCHAR(255) NOT NULL,
    sets INT DEFAULT 0,
    reps INT DEFAULT 0,
    duration_minutes INT DEFAULT 0,
    calories_burned INT DEFAULT 0,
    notes TEXT DEFAULT '',
    logged_at TIMESTAMP DEFAULT NOW()
);
