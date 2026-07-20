const state = { token: "", overview: null, keyPlatform: "grok" };
const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
})[character]);
const platformName = (id) => ({ grok: "Grok", gemini: "Gemini", "chatgpt-image": "ChatGPT 图片" })[id] || id;
const formatDate = (value) => value ? new Intl.DateTimeFormat("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value)) : "—";

function toast(message, error = false) {
  const element = $("#toast");
  element.textContent = message;
  element.className = `toast show${error ? " error" : ""}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { element.className = "toast"; }, 3200);
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.method && options.method !== "GET") headers["x-admin-action-token"] = state.token;
  if (options.body) headers["content-type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `请求失败 (${response.status})`);
  return payload;
}

function renderPlatforms(platforms) {
  $("#platformGrid").innerHTML = platforms.map((platform, index) => {
    const queued = platform.queue?.queued || 0;
    const running = platform.queue?.running || 0;
    const reason = platform.queue?.paused_reason;
    const statusText = { online: "正常", paused: "已暂停", offline: "离线" }[platform.status];
    return `<article class="platform-card ${escapeHtml(platform.accent)}">
      <div class="platform-head">
        <div><span class="platform-index">NODE 0${index + 1}</span><h3>${escapeHtml(platform.name)}</h3><span class="platform-capability">${escapeHtml(platform.capability)}</span></div>
        <span class="status-pill ${escapeHtml(platform.status)}">${statusText}</span>
      </div>
      <div class="platform-metrics">
        <div><span>运行中</span><strong>${running}</strong></div>
        <div><span>排队</span><strong>${queued}</strong></div>
        <div><span>有效 Key</span><strong>${platform.keys.enabled}</strong></div>
      </div>
      <p class="risk-note${reason ? " alert" : ""}">${escapeHtml(reason || (platform.status === "offline" ? "服务未响应；可在此启动。" : "队列与鉴权状态正常。"))}</p>
      <div class="card-actions">
        <button class="button ghost" data-service-action="restart" data-platform="${platform.id}" type="button">重启 / 恢复</button>
        <button class="button ${platform.status === "offline" ? "primary" : "danger"}" data-service-action="${platform.status === "offline" ? "start" : "stop"}" data-platform="${platform.id}" type="button">${platform.status === "offline" ? "启动" : "停止"}</button>
      </div>
    </article>`;
  }).join("");
}

function renderFeed(selector, items, type) {
  const container = $(selector);
  if (!items.length) { container.innerHTML = '<p class="empty">暂无记录</p>'; return; }
  container.innerHTML = items.map((item) => {
    const status = type === "job" ? item.status : item.outcome;
    const title = type === "job" ? `${platformName(item.platform)} · ${item.endpoint}` : `${platformName(item.platform)} · ${item.action}`;
    const detail = type === "job" ? `${item.model || "默认模型"} · ${item.key_id || "系统"}` : (item.details || "操作已记录");
    return `<div class="feed-item"><span class="feed-dot ${escapeHtml(status)}"></span><div class="feed-main"><strong>${escapeHtml(title)}</strong><small>${escapeHtml(detail)}</small></div><span class="feed-time">${formatDate(item.created_at)}</span></div>`;
  }).join("");
}

async function loadOverview(silent = false) {
  try {
    const overview = await request("/api/overview");
    state.overview = overview;
    $("#onlineCount").textContent = overview.summary.online;
    $("#pausedCount").textContent = overview.summary.paused;
    $("#keyCount").textContent = overview.summary.enabled_keys;
    $("#queuedCount").textContent = overview.summary.queued;
    $("#updatedAt").textContent = `本机状态 · ${new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
    renderPlatforms(overview.platforms);
    renderFeed("#jobFeed", overview.recent_jobs, "job");
    renderFeed("#auditFeed", overview.audit_events, "audit");
    if (!silent) toast("状态已刷新");
  } catch (error) {
    $("#updatedAt").textContent = "控制面状态不可用";
    toast(error.message, true);
  }
}

async function loadKeys(platform = state.keyPlatform) {
  state.keyPlatform = platform;
  $$(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.keyPlatform === platform));
  try {
    const payload = await request(`/api/keys/${platform}`);
    const body = $("#keyRows");
    if (!payload.keys.length) { body.innerHTML = '<tr><td colspan="6" class="empty">该平台还没有个人密钥</td></tr>'; return; }
    body.innerHTML = payload.keys.map((key) => `<tr>
      <td>${escapeHtml(key.owner)}</td><td>${escapeHtml(key.department || "—")}</td><td><code>${escapeHtml(key.key_id)}</code></td>
      <td><span class="state-label ${key.enabled ? "enabled" : "disabled"}">${key.enabled ? "ENABLED" : "DISABLED"}</span></td>
      <td>${formatDate(key.last_used_at)}</td>
      <td><div class="key-actions"><button class="mini-button" data-key-action="rotate" data-key-id="${escapeHtml(key.key_id)}" type="button">轮换</button><button class="mini-button" data-key-action="${key.enabled ? "disable" : "enable"}" data-key-id="${escapeHtml(key.key_id)}" type="button">${key.enabled ? "停用" : "启用"}</button>${key.enabled ? "" : `<button class="mini-button danger" data-key-action="delete" data-key-id="${escapeHtml(key.key_id)}" type="button">删除</button>`}</div></td>
    </tr>`).join("");
  } catch (error) { toast(error.message, true); }
}

async function mutateButton(button, operation) {
  button.disabled = true;
  try { await operation(); } finally { button.disabled = false; }
}

document.addEventListener("click", async (event) => {
  const tab = event.target.closest("[data-key-platform]");
  if (tab) return loadKeys(tab.dataset.keyPlatform);

  const serviceButton = event.target.closest("[data-service-action]");
  if (serviceButton) {
    const { platform, serviceAction } = serviceButton.dataset;
    const label = serviceAction === "stop" ? "停止" : serviceAction === "start" ? "启动" : "重启";
    if (!window.confirm(`确认${label} ${platformName(platform)}？该操作只影响此平台。`)) return;
    return mutateButton(serviceButton, async () => {
      try {
        await request(`/api/platforms/${platform}/${serviceAction}`, { method: "POST" });
        toast(`${platformName(platform)} 已执行${label}`);
        await loadOverview(true);
      } catch (error) { toast(error.message, true); }
    });
  }

  const keyButton = event.target.closest("[data-key-action]");
  if (keyButton) {
    const action = keyButton.dataset.keyAction;
    const keyId = keyButton.dataset.keyId;
    const actionLabel = action === "rotate" ? "轮换" : action === "disable" ? "停用" : action === "delete" ? "永久删除" : "启用";
    const warning = action === "delete" ? "该操作无法恢复，历史审计记录仍会保留。" : "";
    if (!window.confirm(`确认${actionLabel} Key ${keyId}？${warning}`)) return;
    return mutateButton(keyButton, async () => {
      try {
        const payload = action === "delete"
          ? await request(`/api/keys/${state.keyPlatform}/${keyId}`, { method: "DELETE" })
          : await request(`/api/keys/${state.keyPlatform}/${keyId}/${action}`, { method: "POST", body: action === "rotate" ? "{}" : undefined });
        if (payload.api_key) showSecret(payload.api_key);
        toast(action === "delete" ? "停用密钥已永久删除" : "密钥状态已更新");
        await Promise.all([loadKeys(), loadOverview(true)]);
      } catch (error) { toast(error.message, true); }
    });
  }
});

function showSecret(value, verification = null, platform = null) {
  $("#secretValue").textContent = value;
  const verificationElement = $("#secretVerification");
  if (verification?.status === "accepted") {
    const location = platform === "gemini" ? "网关数据库" : "上游原生后台";
    verificationElement.textContent = `${platformName(platform)} 密钥已写入${location}，并通过 800${platform === "grok" ? "1" : platform === "gemini" ? "2" : "3"} 实时验证（HTTP ${verification.http_status}）`;
  } else if (verification?.status === "offline") {
    verificationElement.textContent = `${platformName(platform)} 网关当前离线，密钥已写入但尚未完成运行验证`;
  } else {
    verificationElement.textContent = "";
  }
  $("#secretDialog").showModal();
}

$("#refreshButton").addEventListener("click", () => loadOverview());
$("#newKeyButton").addEventListener("click", () => $("#keyDialog").showModal());
$("#closeSecretButton").addEventListener("click", () => {
  $("#secretValue").textContent = "";
  $("#secretVerification").textContent = "";
  $("#secretDialog").close();
});
$("#copySecretButton").addEventListener("click", async () => {
  try { await navigator.clipboard.writeText($("#secretValue").textContent); toast("密钥已复制"); }
  catch { toast("复制失败，请手动选择文本", true); }
});
$("#keyForm").addEventListener("submit", async (event) => {
  if (event.submitter?.value === "cancel") return;
  event.preventDefault();
  const formElement = event.currentTarget;
  const form = new FormData(formElement);
  const expires = form.get("expires_at");
  const payload = {
    platform: form.get("platform"), owner: form.get("owner"),
    department: form.get("department") || null,
    expires_at: expires ? new Date(expires).toISOString() : null,
  };
  const button = $("#createKeySubmit");
  await mutateButton(button, async () => {
    try {
      const created = await request("/api/keys", { method: "POST", body: JSON.stringify(payload) });
      formElement.reset();
      $("#keyDialog").close();
      state.keyPlatform = payload.platform;
      showSecret(created.api_key, created.verification, payload.platform);
      const verification = created.verification?.status;
      if (verification === "accepted") toast(`${platformName(payload.platform)} 密钥已写入真实控制面并通过运行服务验证`);
      else toast(`${platformName(payload.platform)} 密钥已写入；平台当前离线，启动后请验证`, true);
      await Promise.all([loadKeys(payload.platform), loadOverview(true)]);
    } catch (error) { toast(error.message, true); }
  });
});

(async function initialize() {
  try {
    state.token = (await request("/api/session")).action_token;
    await Promise.all([loadOverview(true), loadKeys()]);
    setInterval(() => loadOverview(true), 10000);
  } catch (error) { toast(error.message, true); }
})();
