/** MishPulse web UI — hash-router SPA. */

const THEME_STORAGE_KEY = "mishpulse-theme";

function getAppEl() {
  return document.getElementById("app-content");
}

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
  const cls =
    health === "alive"
      ? "badge-alive"
      : health === "warning"
        ? "badge-warning"
        : health === "error" || health === "dead"
          ? "badge-error"
          : "badge-neutral";
  return `<span class="badge ${cls}">${escapeHtml(HEALTH_LABELS[health] || health)}</span>`;
}

function enabledBadge(enabled) {
  return enabled
    ? '<span class="badge badge-alive">Включён</span>'
    : '<span class="badge badge-neutral">Отключён</span>';
}

function levelClass(level) {
  if (level === "ok") return "status-level-ok";
  if (level === "warning") return "status-level-warning";
  if (level === "error") return "status-level-error";
  return "";
}

function summarizeProjects(projects) {
  const enabled = projects.filter((p) => p.enabled);
  const dead = enabled.filter((p) => p.health === "dead").length;
  const errors = enabled.filter((p) => p.health === "error").length;
  const warnings = enabled.filter((p) => p.health === "warning").length;
  const alive = enabled.filter((p) => p.health === "alive").length;
  const problemCount = dead + errors;

  let state = "ok";
  let headline = "Всё работает штатно";
  if (!projects.length) {
    state = "empty";
    headline = "Проектов пока нет";
  } else if (problemCount > 0) {
    state = "bad";
    headline = problemCount === 1 ? "1 проект требует внимания" : `${problemCount} проектов требуют внимания`;
  } else if (warnings > 0) {
    state = "warn";
    headline = warnings === 1 ? "1 предупреждение" : `${warnings} предупреждений`;
  } else if (enabled.length === 0) {
    state = "empty";
    headline = "Все проекты отключены";
  }

  return {
    state,
    headline,
    total: projects.length,
    enabled: enabled.length,
    alive,
    dead,
    errors,
    warnings,
    problemCount,
  };
}

function statusHero(summary) {
  const figure =
    summary.state === "bad"
      ? String(summary.problemCount)
      : summary.state === "warn"
        ? String(summary.warnings)
        : summary.state === "empty"
          ? "—"
          : String(summary.alive);

  const detail =
    summary.total === 0
      ? "Создайте первый проект для мониторинга heartbeat"
      : `${summary.total} проектов · ${summary.enabled} включено · ${summary.alive} живых · ${summary.dead + summary.errors} проблем`;

  return `
    <div class="status-hero ${escapeHtml(summary.state)}">
      <span class="status-dot" aria-hidden="true"></span>
      <div class="status-hero-body">
        <h2 class="status-hero-headline">${escapeHtml(summary.headline)}</h2>
        <p class="status-hero-summary">${escapeHtml(detail)}</p>
      </div>
      <div class="status-hero-figure">${escapeHtml(figure)}</div>
    </div>`;
}

function statGrid(summary) {
  if (!summary.total) return "";
  return `
    <div class="stat-grid">
      <div class="stat-card accent-cap">
        <span class="stat-label">Всего проектов</span>
        <span class="stat-value">${summary.total}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Включено</span>
        <span class="stat-value">${summary.enabled}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">Живых</span>
        <span class="stat-value">${summary.alive}</span>
      </div>
      <div class="stat-card ${summary.problemCount ? "error-cap" : ""}">
        <span class="stat-label">Проблем</span>
        <span class="stat-value ${summary.problemCount ? "error-value" : ""}">${summary.problemCount}</span>
      </div>
    </div>`;
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
  document.querySelectorAll(".nav-tab[data-route]").forEach((link) => {
    const target = link.getAttribute("data-route");
    const active =
      target === route ||
      (target === "/" && route === "/") ||
      (target !== "/" && route.startsWith(target));
    link.classList.toggle("active", active);
  });
}

function renderLoading() {
  getAppEl().innerHTML = `<div class="loading-state">Загрузка…</div>`;
}

function renderError(message) {
  getAppEl().innerHTML = `<div class="alert alert-error">${escapeHtml(message)}</div>`;
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
  const summary = summarizeProjects(projects);

  if (!projects.length) {
    getAppEl().innerHTML = `
      <div class="page-hero">
        <div>
          <h1>Проекты</h1>
          <p class="subtitle">Мониторинг heartbeat</p>
        </div>
        <a class="btn btn-primary" href="#/projects/new">Новый проект</a>
      </div>
      ${statusHero(summary)}
      <div class="empty-state">
        <p>Создайте первый проект и получите ссылку для heartbeat.</p>
        <p class="actions"><a class="btn btn-primary" href="#/projects/new">Создать проект</a></p>
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
        <td class="num">${escapeHtml(project.timeout_seconds || "—")}</td>
        <td>${escapeHtml(project.last_message || "—")}</td>
        <td><a class="btn" href="#/projects/${escapeHtml(project.token)}">Управление</a></td>
      </tr>`
    )
    .join("");

  getAppEl().innerHTML = `
    <div class="page-hero">
      <div>
        <h1>Проекты</h1>
        <p class="subtitle">Обновляется каждые 30 с · всего ${projects.length}</p>
      </div>
      <a class="btn btn-primary" href="#/projects/new">Новый проект</a>
    </div>
    ${statusHero(summary)}
    ${statGrid(summary)}
    <div class="data-table-wrap">
      <table class="data-table">
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
  getAppEl().innerHTML = `
    <div class="page-hero">
      <div>
        <h1>Новый проект</h1>
        <p class="subtitle">После создания — уникальная ссылка для heartbeat</p>
      </div>
    </div>
    <div class="card">
      <form id="create-form">
        <h3 class="section-title">Основные настройки</h3>
        ${projectSettingsForm({ enabled: true }, "new-project")}
        <h3 class="section-title">Уведомления (опционально)</h3>
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

  const [summaryList, notifications, statuses] = await Promise.all([
    api("/projects/summary"),
    api(`/projects/${token}/notifications`),
    api(`/projects/${token}/statuses`),
  ]);

  const project = summaryList.find((item) => item.token === token);
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
          <strong class="${levelClass(status.level)}">${escapeHtml(LEVEL_LABELS[status.level] || status.level)}</strong>
          <span class="muted"> · ${escapeHtml(formatDate(status.timestamp))}</span>
          <div>${escapeHtml(status.message || "—")}</div>
        </li>`
        )
        .join("")
    : `<li class="muted">Статусов пока нет</li>`;

  const heroState =
    project.health === "dead" || project.health === "error"
      ? "bad"
      : project.health === "warning"
        ? "warn"
        : project.enabled
          ? "ok"
          : "empty";

  const heroHeadline =
    project.health === "dead"
      ? "Проект не отвечает"
      : project.health === "error"
        ? "Ошибка в последнем статусе"
        : project.health === "warning"
          ? "Предупреждение"
          : project.enabled
            ? "Работает штатно"
            : "Мониторинг отключён";

  getAppEl().innerHTML = `
    ${created ? '<div class="alert alert-success">Проект создан. Сохраните ссылку для heartbeat.</div>' : ""}
    <div class="page-hero">
      <div>
        <h1>${escapeHtml(project.name)}</h1>
        <p class="subtitle">ID: ${escapeHtml(project.id)}</p>
      </div>
      <div class="detail-badges">${enabledBadge(project.enabled)} ${badge(project.health)}</div>
    </div>

    <div class="status-hero ${heroState}">
      <span class="status-dot" aria-hidden="true"></span>
      <div class="status-hero-body">
        <h2 class="status-hero-headline">${escapeHtml(heroHeadline)}</h2>
        <p class="status-hero-summary">Последний пульс: ${escapeHtml(formatDate(project.last_seen))} · timeout ${escapeHtml(project.timeout_seconds || "глобальный")} с · retention ${escapeHtml(project.retention_days ?? "глобальный")} дн.</p>
      </div>
    </div>

    <div class="card">
      <p class="muted">Последнее сообщение: ${escapeHtml(project.last_message || "—")}</p>
      <label class="field-label">URL для heartbeat</label>
      <div class="code-box">
        <span id="heartbeat-url">${escapeHtml(heartbeatUrl)}</span>
        <button class="btn" type="button" id="copy-heartbeat">Копировать</button>
      </div>
      <pre class="code-snippet">curl -X POST '${escapeHtml(heartbeatUrl)}' \\
  -H 'Content-Type: application/json' \\
  -d '{"level":"ok","message":"alive"}'</pre>
    </div>

    <div class="grid grid-2">
      <div class="card">
        <h3 class="section-title">Основные настройки</h3>
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
        <h3 class="section-title">Уведомления</h3>
        <form id="notifications-form">
          ${notificationsForm(notifications, "edit")}
          <div class="actions">
            <button class="btn btn-primary" type="submit">Сохранить</button>
          </div>
        </form>
        <div id="notifications-message"></div>
      </div>

      <div class="card">
        <h3 class="section-title">История статусов</h3>
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
  logout.classList.toggle("hidden", !(authState.required && authState.authenticated));
}

function initThemeToggle() {
  const button = document.getElementById("btn-theme");
  if (!button) return;

  button.addEventListener("click", () => {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem(THEME_STORAGE_KEY, "light");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem(THEME_STORAGE_KEY, "dark");
    }
  });
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
  const main = document.getElementById("main");
  main.innerHTML = `
    <div class="login-wrap">
      <div class="login-card">
        <h1 class="section-title">Вход</h1>
        <p class="muted">Пароль администратора MishPulse</p>
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
      </div>
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
      main.innerHTML = '<div id="app-content" class="view"></div>';
      location.hash = "#/";
    } catch (error) {
      messageEl.innerHTML = `<div class="alert alert-error">${escapeHtml(error.message)}</div>`;
    }
  });
}

function ensureAppContent() {
  const main = document.getElementById("main");
  if (!document.getElementById("app-content")) {
    main.innerHTML = '<div id="app-content" class="view"></div>';
  }
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

    ensureAppContent();

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

initThemeToggle();
window.addEventListener("hashchange", router);
router();

setInterval(() => {
  const path = (location.hash.replace(/^#/, "") || "/").split("?")[0];
  if (path === "/" || path === "") router();
}, 30000);
