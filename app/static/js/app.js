/** MishPulse web UI — hash-router SPA. */

const appEl = document.getElementById("app");

const HEALTH_LABELS = {
  alive: "Жив",
  warning: "Предупреждение",
  error: "Ошибка",
  dead: "Не отвечает",
};

const LEVEL_LABELS = {
  ok: "OK",
  warning: "Warning",
  error: "Error",
};

const AUTH_STORAGE_KEY = "mishpulse_password";

let authState = { required: false, authenticated: true };

function authHeaders() {
  const password = sessionStorage.getItem(AUTH_STORAGE_KEY);
  if (!password) return {};
  return { Authorization: `Bearer ${password}` };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
    ...options,
  });
  if (response.status === 401) {
    sessionStorage.removeItem(AUTH_STORAGE_KEY);
    authState = { required: true, authenticated: false };
    if (!location.hash.includes("/login")) {
      location.hash = "#/login";
    }
    throw new Error("Требуется авторизация");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (response.status === 204) return null;
  const text = await response.text();
  return text ? JSON.parse(text) : null;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatDate(iso) {
  if (!iso) return "—";
  const date = new Date(iso);
  return date.toLocaleString("ru-RU");
}

function badge(health) {
  return `<span class="badge badge-${escapeHtml(health)}">${escapeHtml(HEALTH_LABELS[health] || health)}</span>`;
}

function enabledBadge(enabled) {
  return enabled
    ? '<span class="badge badge-alive">Включён</span>'
    : '<span class="badge badge-dead">Отключён</span>';
}

function projectSettingsForm(values = {}, idPrefix = "settings") {
  const v = (key) => escapeHtml(values[key] ?? "");
  return `
    <div class="grid grid-2">
      <div class="form-group">
        <label for="${idPrefix}-name">Название</label>
        <input id="${idPrefix}-name" name="name" value="${v("name")}" required maxlength="200">
      </div>
      <div class="form-group">
        <label for="${idPrefix}-enabled">Мониторинг</label>
        <select id="${idPrefix}-enabled" name="enabled">
          <option value="true" ${values.enabled === false ? "" : "selected"}>Включён</option>
          <option value="false" ${values.enabled === false ? "selected" : ""}>Отключён</option>
        </select>
      </div>
      <div class="form-group">
        <label for="${idPrefix}-timeout">Timeout, секунд</label>
        <input id="${idPrefix}-timeout" name="timeout_seconds" type="number" min="1" step="1" value="${v("timeout_seconds")}" placeholder="глобальный">
      </div>
      <div class="form-group">
        <label for="${idPrefix}-retention">Retention истории, дней</label>
        <input id="${idPrefix}-retention" name="retention_days" type="number" min="0" step="1" value="${v("retention_days")}" placeholder="глобальный; 0 = не чистить">
      </div>
    </div>`;
}

function readProjectSettings(form, includeEmpty = false) {
  const data = new FormData(form);
  const payload = {};
  const name = String(data.get("name") || "").trim();
  if (name || includeEmpty) payload.name = name;
  if (data.has("enabled")) payload.enabled = String(data.get("enabled")) === "true";

  for (const key of ["timeout_seconds", "retention_days"]) {
    const raw = String(data.get(key) || "").trim();
    if (raw) {
      payload[key] = key === "timeout_seconds" ? Number(raw) : Number.parseInt(raw, 10);
    } else if (includeEmpty) {
      payload[key] = null;
    }
  }
  return payload;
}

function setActiveNav(route) {
  document.querySelectorAll(".nav a[data-route]").forEach((link) => {
    const target = link.getAttribute("data-route");
    const active =
      target === route ||
      (target === "/" && route === "/") ||
      (target !== "/" && route.startsWith(target));
    link.classList.toggle("active", active);
  });
}

function renderLoading() {
  appEl.innerHTML = `<div class="card"><p class="muted">Загрузка…</p></div>`;
}

function renderError(message) {
  appEl.innerHTML = `<div class="alert alert-error">${escapeHtml(message)}</div>`;
}

async function copyText(text) {
  await navigator.clipboard.writeText(text);
}

function extractToken(linkOrPath) {
  const match = String(linkOrPath).match(/\/projects\/([^/]+)\//);
  return match ? match[1] : null;
}

async function pageDashboard() {
  renderLoading();
  setActiveNav("/");
  const projects = await api("/projects/summary");

  if (!projects.length) {
    appEl.innerHTML = `
      <div class="card empty">
        <h2>Проектов пока нет</h2>
        <p class="muted">Создайте первый проект и получите ссылку для heartbeat.</p>
        <p><a class="btn btn-primary" href="#/projects/new">Создать проект</a></p>
      </div>`;
    return;
  }

  const rows = projects
    .map(
      (project) => `
      <tr>
        <td><a href="#/projects/${escapeHtml(project.token)}">${escapeHtml(project.name)}</a></td>
        <td>${enabledBadge(project.enabled)} ${badge(project.health)}</td>
        <td>${escapeHtml(formatDate(project.last_seen))}</td>
        <td>${escapeHtml(project.timeout_seconds || "глобальный")}</td>
        <td>${escapeHtml(project.last_message || "—")}</td>
        <td><a class="btn" href="#/projects/${escapeHtml(project.token)}">Управление</a></td>
      </tr>`
    )
    .join("");

  appEl.innerHTML = `
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap;">
        <div>
          <h2>Проекты</h2>
          <p class="muted">Обновляется при переходе между страницами. Всего: ${projects.length}</p>
        </div>
        <a class="btn btn-primary" href="#/projects/new">+ Новый проект</a>
      </div>
      <table>
        <thead>
          <tr>
            <th>Имя</th>
            <th>Состояние</th>
            <th>Последний пульс</th>
            <th>Timeout</th>
            <th>Сообщение</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function notificationsForm(values = {}, idPrefix = "nf") {
  const v = (key) => escapeHtml(values[key] ?? "");
  return `
    <div class="grid grid-2">
      <div class="form-group">
        <label for="${idPrefix}-ntfy-topic">ntfy topic</label>
        <input id="${idPrefix}-ntfy-topic" name="ntfy_topic" value="${v("ntfy_topic")}" placeholder="my-service-alerts">
      </div>
      <div class="form-group">
        <label for="${idPrefix}-ntfy-server">ntfy server (опционально)</label>
        <input id="${idPrefix}-ntfy-server" name="ntfy_server" value="${v("ntfy_server")}" placeholder="https://ntfy.sh">
      </div>
      <div class="form-group">
        <label for="${idPrefix}-tg-chat">Telegram chat ID</label>
        <input id="${idPrefix}-tg-chat" name="telegram_chat_id" value="${v("telegram_chat_id")}" placeholder="123456789">
      </div>
      <div class="form-group">
        <label for="${idPrefix}-tg-token">Telegram bot token (опционально)</label>
        <input id="${idPrefix}-tg-token" name="telegram_bot_token" value="${v("telegram_bot_token")}" placeholder="123:ABC">
      </div>
    </div>
    <p class="muted">Алерты уходят при error, warning и когда проект перестаёт отвечать.</p>`;
}

function readNotifications(form) {
  const data = new FormData(form);
  const payload = {};
  for (const key of ["ntfy_topic", "ntfy_server", "telegram_chat_id", "telegram_bot_token"]) {
    const value = String(data.get(key) || "").trim();
    if (value) payload[key] = value;
  }
  return payload;
}

async function pageNewProject() {
  setActiveNav("/projects/new");
  appEl.innerHTML = `
    <div class="card">
      <h2>Новый проект</h2>
      <p class="muted">После создания вы получите уникальную ссылку для отправки heartbeat.</p>
      <form id="create-form">
        <h3>Основные настройки</h3>
        ${projectSettingsForm({ enabled: true }, "new-project")}
        <h3>Уведомления (опционально)</h3>
        ${notificationsForm({}, "new")}
        <div class="actions">
          <button class="btn btn-primary" type="submit">Создать</button>
          <a class="btn" href="#/">Отмена</a>
        </div>
      </form>
      <div id="form-message"></div>
    </div>`;

  const form = document.getElementById("create-form");
  const messageEl = document.getElementById("form-message");

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    messageEl.innerHTML = "";
    const body = readProjectSettings(form);
    const notifications = readNotifications(form);
    if (Object.keys(notifications).length) body.notifications = notifications;

    try {
      const project = await api("/projects", { method: "POST", body: JSON.stringify(body) });
      const token = extractToken(project.link);
      location.hash = `#/projects/${token}?created=1`;
    } catch (error) {
      messageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });
}

async function pageProjectDetail(token) {
  renderLoading();
  setActiveNav("/");

  const [summary, notifications, statuses] = await Promise.all([
    api("/projects/summary"),
    api(`/projects/${token}/notifications`),
    api(`/projects/${token}/statuses`),
  ]);

  const project = summary.find((item) => item.token === token);
  if (!project) {
    renderError("Проект не найден. Проверьте ссылку или token.");
    return;
  }

  const heartbeatUrl = `${location.origin}/projects/${token}/statuses`;
  const created = new URLSearchParams(location.hash.split("?")[1] || "").get("created");
  const statusItems = statuses.length
    ? statuses
        .slice()
        .reverse()
        .map(
          (status) => `
        <li>
          <strong>${escapeHtml(LEVEL_LABELS[status.level] || status.level)}</strong>
          <span class="muted"> · ${escapeHtml(formatDate(status.timestamp))}</span>
          <div>${escapeHtml(status.message || "—")}</div>
        </li>`
        )
        .join("")
    : `<li class="muted">Статусов пока нет</li>`;

  appEl.innerHTML = `
    ${created ? '<div class="alert alert-success">Проект создан. Сохраните ссылку для heartbeat.</div>' : ""}
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;align-items:flex-start;">
        <div>
          <h2>${escapeHtml(project.name)}</h2>
          <p class="muted">ID: ${escapeHtml(project.id)}</p>
        </div>
        <div>${enabledBadge(project.enabled)} ${badge(project.health)}</div>
      </div>
      <p>Последний пульс: <strong>${escapeHtml(formatDate(project.last_seen))}</strong></p>
      <p>Timeout: <strong>${escapeHtml(project.timeout_seconds || "глобальный")}</strong> сек. · Retention: <strong>${escapeHtml(project.retention_days ?? "глобальный")}</strong> дней</p>
      <p>Последнее сообщение: ${escapeHtml(project.last_message || "—")}</p>
      <label class="muted">URL для heartbeat</label>
      <div class="code-box">
        <span id="heartbeat-url">${escapeHtml(heartbeatUrl)}</span>
        <button class="btn" type="button" id="copy-heartbeat">Копировать</button>
      </div>
      <pre class="muted" style="margin-top:0.75rem;white-space:pre-wrap;">curl -X POST '${escapeHtml(heartbeatUrl)}' \\
  -H 'Content-Type: application/json' \\
  -d '{"level":"ok","message":"alive"}'</pre>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <h3>Основные настройки</h3>
        <form id="project-settings-form">
          ${projectSettingsForm(project, "edit-project")}
          <div class="actions">
            <button class="btn btn-primary" type="submit">Сохранить проект</button>
            <button class="btn" type="button" id="send-test-notification">Тест уведомлений</button>
            <button class="btn btn-danger" type="button" id="delete-project">Удалить</button>
          </div>
        </form>
        <div id="project-settings-message"></div>
      </div>

      <div class="card">
        <h3>Уведомления</h3>
        <form id="notifications-form">
          ${notificationsForm(notifications, "edit")}
          <div class="actions">
            <button class="btn btn-primary" type="submit">Сохранить</button>
          </div>
        </form>
        <div id="notifications-message"></div>
      </div>

      <div class="card">
        <h3>История статусов</h3>
        <ul class="status-list">${statusItems}</ul>
      </div>
    </div>

    <p><a class="btn" href="#/">← К списку проектов</a></p>`;

  document.getElementById("copy-heartbeat").addEventListener("click", async () => {
    await copyText(heartbeatUrl);
    const button = document.getElementById("copy-heartbeat");
    button.textContent = "Скопировано";
    setTimeout(() => {
      button.textContent = "Копировать";
    }, 1500);
  });

  const projectSettingsFormEl = document.getElementById("project-settings-form");
  const projectSettingsMessageEl = document.getElementById("project-settings-message");
  projectSettingsFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    projectSettingsMessageEl.innerHTML = "";
    try {
      await api(`/projects/${token}`, {
        method: "PATCH",
        body: JSON.stringify(readProjectSettings(projectSettingsFormEl, true)),
      });
      projectSettingsMessageEl.innerHTML =
        '<div class="alert alert-success">Настройки проекта сохранены.</div>';
      setTimeout(() => pageProjectDetail(token), 700);
    } catch (error) {
      projectSettingsMessageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });

  document.getElementById("send-test-notification").addEventListener("click", async () => {
    projectSettingsMessageEl.innerHTML = "";
    try {
      await api(`/projects/${token}/test-notification`, { method: "POST" });
      projectSettingsMessageEl.innerHTML =
        '<div class="alert alert-success">Тестовое уведомление отправлено.</div>';
    } catch (error) {
      projectSettingsMessageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });

  document.getElementById("delete-project").addEventListener("click", async () => {
    if (!confirm(`Удалить проект «${project.name}» и всю историю статусов?`)) return;
    projectSettingsMessageEl.innerHTML = "";
    try {
      await api(`/projects/${token}`, { method: "DELETE" });
      location.hash = "#/";
    } catch (error) {
      projectSettingsMessageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });

  const notificationsFormEl = document.getElementById("notifications-form");
  const notificationsMessageEl = document.getElementById("notifications-message");
  notificationsFormEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    notificationsMessageEl.innerHTML = "";
    try {
      await api(`/projects/${token}/notifications`, {
        method: "PATCH",
        body: JSON.stringify(readNotifications(notificationsFormEl)),
      });
      notificationsMessageEl.innerHTML =
        '<div class="alert alert-success">Настройки уведомлений сохранены.</div>';
    } catch (error) {
      notificationsMessageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });
}

function updateNavAuth() {
  const logout = document.getElementById("logout-btn");
  if (!logout) return;
  logout.style.display = authState.required && authState.authenticated ? "inline-flex" : "none";
}

async function refreshAuthState() {
  const response = await fetch("/auth/status", { headers: authHeaders() });
  if (response.ok) {
    authState = await response.json();
  }
  updateNavAuth();
}

async function pageLogin() {
  setActiveNav("");
  appEl.innerHTML = `
    <div class="card" style="max-width:420px;margin:2rem auto;">
      <h2>Вход</h2>
      <p class="muted">Введите пароль администратора MishPulse.</p>
      <form id="login-form">
        <div class="form-group">
          <label for="login-password">Пароль</label>
          <input id="login-password" name="password" type="password" required autocomplete="current-password">
        </div>
        <div class="actions">
          <button class="btn btn-primary" type="submit">Войти</button>
        </div>
      </form>
      <div id="login-message"></div>
    </div>`;

  document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const messageEl = document.getElementById("login-message");
    messageEl.innerHTML = "";
    const password = String(new FormData(event.target).get("password") || "");
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "Неверный пароль");
      }
      sessionStorage.setItem(AUTH_STORAGE_KEY, password);
      await refreshAuthState();
      location.hash = "#/";
    } catch (error) {
      messageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });
}

async function router() {
  const hash = location.hash.replace(/^#/, "") || "/";
  const [path] = hash.split("?");
  const segments = path.split("/").filter(Boolean);

  try {
    await refreshAuthState();

    if (path === "/login") {
      if (!authState.required || authState.authenticated) {
        location.hash = "#/";
        return;
      }
      await pageLogin();
      return;
    }

    if (authState.required && !authState.authenticated) {
      location.hash = "#/login";
      await pageLogin();
      return;
    }

    if (path === "/" || path === "") {
      await pageDashboard();
      return;
    }
    if (path === "/projects/new") {
      await pageNewProject();
      return;
    }
    if (segments[0] === "projects" && segments[1] && segments[1] !== "new") {
      await pageProjectDetail(segments[1]);
      return;
    }
    renderError(`Страница не найдена: ${path}`);
  } catch (error) {
    if (error.message !== "Требуется авторизация") {
      renderError(error.message);
    }
  }
}

document.getElementById("logout-btn")?.addEventListener("click", () => {
  sessionStorage.removeItem(AUTH_STORAGE_KEY);
  authState = { required: true, authenticated: false };
  location.hash = "#/login";
});

window.addEventListener("hashchange", router);
router();

// Автообновление дашборда каждые 30 секунд, если открыт список проектов
setInterval(() => {
  const path = (location.hash.replace(/^#/, "") || "/").split("?")[0];
  if (path === "/" || path === "") router();
}, 30000);
