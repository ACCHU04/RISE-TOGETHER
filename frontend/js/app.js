// Rise Circle — Core JS

const API = 'http://localhost:8000';
const SOCKET_URL = 'http://localhost:3000';

// ─── Auth Helpers ────────────────────────────────────────────────────────────

const Auth = {
  getToken: () => localStorage.getItem('rc_token'),
  getUser: () => JSON.parse(localStorage.getItem('rc_user') || 'null'),
  isLoggedIn: () => !!localStorage.getItem('rc_token'),
  save: (token, user) => {
    localStorage.setItem('rc_token', token);
    localStorage.setItem('rc_user', JSON.stringify(user));
  },
  logout: () => {
    localStorage.removeItem('rc_token');
    localStorage.removeItem('rc_user');
    window.location.href = '/frontend/pages/login.html';
  },
  requireAuth: () => {
    if (!Auth.isLoggedIn()) {
      window.location.href = '/frontend/pages/login.html';
      return false;
    }
    return true;
  }
};

// ─── API Client ──────────────────────────────────────────────────────────────

const api = async (method, path, body = null) => {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  const token = Auth.getToken();
  if (token) opts.headers['Authorization'] = `Bearer ${token}`;
  if (body) opts.body = JSON.stringify(body);

  try {
    const res = await fetch(API + path, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
  } catch (err) {
    throw err;
  }
};

// ─── Toast System ────────────────────────────────────────────────────────────

const Toast = {
  container: null,
  init() {
    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    document.body.appendChild(this.container);
  },
  show(message, type = 'info', duration = 3000) {
    if (!this.container) this.init();
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = `<span>${icons[type]}</span><span>${message}</span>`;
    this.container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(20px)';
      toast.style.transition = 'all 0.3s';
      setTimeout(() => toast.remove(), 300);
    }, duration);
  },
  success: (msg) => Toast.show(msg, 'success'),
  error: (msg) => Toast.show(msg, 'error'),
  info: (msg) => Toast.show(msg, 'info'),
};

// ─── Modal System ────────────────────────────────────────────────────────────

const Modal = {
  show(content, title) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal">
        <button class="modal-close" onclick="Modal.close()">✕</button>
        <h3 class="modal-title">${title || ''}</h3>
        ${content}
      </div>
    `;
    overlay.addEventListener('click', e => { if (e.target === overlay) Modal.close(); });
    document.body.appendChild(overlay);
    document.body.style.overflow = 'hidden';
    this._current = overlay;
  },
  close() {
    if (this._current) {
      this._current.remove();
      this._current = null;
      document.body.style.overflow = '';
    }
  }
};

// ─── Sidebar & Nav ───────────────────────────────────────────────────────────

function initSidebar() {
  const user = Auth.getUser();
  if (!user) return;

  const initials = user.username ? user.username[0].toUpperCase() : 'U';

  document.querySelectorAll('.sidebar-user-initials').forEach(el => el.textContent = initials);
  document.querySelectorAll('.sidebar-user-name').forEach(el => el.textContent = user.username || 'User');

  // Active nav item
  const currentPage = window.location.pathname.split('/').pop();
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href') || item.dataset.page;
    if (href && href.includes(currentPage)) {
      item.classList.add('active');
    }
  });
}

// ─── Sidebar HTML Template ───────────────────────────────────────────────────

function getSidebarHTML() {
  const pages = [
    { icon: '⚡', label: 'Dashboard', href: 'dashboard.html' },
    { icon: '📋', label: 'Tasks', href: 'tasks.html' },
    { icon: '⏱', label: 'Focus Timer', href: 'focus.html' },
    { icon: '🌙', label: 'Wake Alarm', href: 'alarm.html' },
    { icon: '🔥', label: 'Habits', href: 'habits.html' },
    { icon: '👥', label: 'Friends & Groups', href: 'groups.html' },
    { icon: '💬', label: 'Community', href: 'community.html' },
    { icon: '💪', label: 'Exercise', href: 'exercise.html' },
    { icon: '🤖', label: 'AI Coach', href: 'chatbot.html' },
    { icon: '🏅', label: 'Achievements', href: 'achievements.html' },
    { icon: '📊', label: 'Analytics', href: 'analytics.html' },
  ];

  return `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-logo">
        <div class="logo-text">Rise Circle</div>
        <div class="logo-sub">Discipline Platform</div>
      </div>
      <nav class="sidebar-nav">
        <div class="nav-section-label">Menu</div>
        ${pages.map(p => `
          <a href="${p.href}" class="nav-item">
            <span class="nav-icon">${p.icon}</span>
            <span>${p.label}</span>
          </a>
        `).join('')}
        <div class="nav-section-label" style="margin-top:12px">Account</div>
        <div class="nav-item" onclick="Auth.logout()">
          <span class="nav-icon">🚪</span>
          <span>Logout</span>
        </div>
      </nav>
      <div class="sidebar-user">
        <div class="sidebar-user-info">
          <div class="user-avatar sidebar-user-initials">U</div>
          <div>
            <div class="user-name sidebar-user-name">Loading...</div>
            <div class="user-streak">🔥 Loading streak...</div>
          </div>
        </div>
      </div>
    </aside>
  `;
}

// ─── Date Helpers ────────────────────────────────────────────────────────────

const dateUtils = {
  today: () => new Date().toISOString().split('T')[0],
  format: (d) => {
    const date = new Date(d);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  },
  formatTime: (ts) => {
    if (!ts) return '—';
    const d = new Date(ts);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  },
  monthKey: () => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`;
  }
};

// ─── Score Ring ───────────────────────────────────────────────────────────────

function renderScoreRing(score, size = 120, color = '#f59e0b') {
  const r = (size / 2) - 10;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  return `
    <div class="score-ring" style="width:${size}px;height:${size}px;">
      <svg width="${size}" height="${size}">
        <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8"/>
        <circle cx="${size/2}" cy="${size/2}" r="${r}" fill="none" stroke="${color}" stroke-width="8"
          stroke-dasharray="${fill} ${circ}" stroke-linecap="round"/>
      </svg>
      <div class="score-text">
        <div style="font-family:'Syne',sans-serif;font-size:${size < 100 ? 18 : 24}px;font-weight:800;color:${color}">${score}%</div>
        <div style="font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px">Score</div>
      </div>
    </div>
  `;
}

// ─── Productivity Score Calculator ───────────────────────────────────────────

function calcProductivityScore(data) {
  let score = 0;
  // Tasks (40%)
  if (data.tasks_total > 0) score += (data.tasks_completed / data.tasks_total) * 40;
  // Wake (30%)
  if (data.wake?.status === 'on_time') score += 30;
  else if (data.wake?.status === 'late') score += 15;
  // Focus (30%)
  const focusPct = Math.min(data.focus_minutes / 120, 1); // 2 hours = 100%
  score += focusPct * 30;
  return Math.round(score);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  Toast.init();
  initSidebar();
});
