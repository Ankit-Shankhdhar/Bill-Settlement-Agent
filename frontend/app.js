const chat    = document.querySelector("#chat");
const form    = document.querySelector("#chat-form");
const input   = document.querySelector("#message-input");
const statusEl = document.querySelector("#status");
const API_BASE = window.location.port === "5500"
  ? "http://127.0.0.1:8000"
  : "";

// ─── Helpers ───────────────────────────────────────────────

const money = (value) => `₹${Number(value || 0).toFixed(2)}`;

/** Escape HTML special characters to prevent XSS. */
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[c]));
}

/**
 * Very light markup: turns **text** into <strong>text</strong>.
 * Does NOT attempt full markdown to stay safe and simple.
 */
function lightMarkup(text) {
  return escapeHtml(text)
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
}

/** Update status badge with a state: "ready" | "thinking" | "error" */
function setStatus(state) {
  statusEl.className = "status" + (state !== "ready" ? ` ${state}` : "");
  const labels = { ready: "Ready", thinking: "Thinking…", error: "Error" };
  statusEl.innerHTML = `<i></i> ${labels[state] || "Ready"}`;
}

// ─── Chat Message Helpers ───────────────────────────────────

function addMessage(role, content) {
  const row = document.createElement("div");
  row.className = `message ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = role === "user" ? "Y" : "S";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = lightMarkup(content);

  row.append(avatar, bubble);
  chat.append(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

/** Show an animated typing indicator; returns the element so it can be removed. */
function addTypingIndicator() {
  const row = document.createElement("div");
  row.className = "message assistant";
  row.id = "typing-indicator";

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = "S";

  const bubble = document.createElement("div");
  bubble.className = "bubble typing";
  bubble.innerHTML = "<span></span><span></span><span></span>";

  row.append(avatar, bubble);
  chat.append(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

function removeTypingIndicator() {
  const el = document.getElementById("typing-indicator");
  if (el) el.remove();
}

// ─── State Rendering ────────────────────────────────────────

function renderState(state) {
  const summary = state.summary;

  document.querySelector("#total").textContent        = money(summary?.total);
  document.querySelector("#fair-share").textContent   = money(summary?.fair_share);
  document.querySelector("#people-count").textContent = Object.keys(summary?.people || {}).length;

  // Payments
  const payments = document.querySelector("#payments");
  if (state.expenses.length) {
    payments.className = "payments";
    payments.innerHTML = state.expenses
      .map((item) => `<div class="payment"><span>${escapeHtml(item.person)}</span><strong>${money(item.amount)}</strong></div>`)
      .join("");
  } else {
    payments.className = "payments empty";
    payments.textContent = "Payments will appear here.";
  }

  // Settlements
  const settlements = document.querySelector("#settlements");
  if (summary?.settlements?.length) {
    settlements.className = "settlements";
    settlements.innerHTML = summary.settlements
      .map((item) => `<div class="settlement"><span>${escapeHtml(item.from)} → ${escapeHtml(item.to)}</span><strong>${money(item.amount)}</strong></div>`)
      .join("");
  } else {
    settlements.className = "settlements empty";
    settlements.textContent = "Ask the agent to settle the bill.";
  }
}

function renderHistory(history) {
  const el = document.querySelector("#history");
  if (!history.length) {
    el.className = "history empty";
    el.textContent = "Your completed bills will appear here.";
    return;
  }

  el.className = "history";
  el.innerHTML = history
    .map((bill) => {
      const people      = Object.keys(bill.people || {}).join(", ");
      const repayments  = bill.settlements?.length || 0;
      return `<div class="history-item">
        <div>
          <strong>${money(bill.total)}</strong>
          <span>${escapeHtml(bill.date)}</span>
          <small>${escapeHtml(people)}</small>
        </div>
        <em>${repayments} repayment${repayments === 1 ? "" : "s"}</em>
      </div>`;
    })
    .join("");
}

// ─── API Calls ──────────────────────────────────────────────

async function loadState() {
  const state = await apiRequest("/api/state");
  if (state.messages?.length) {
    chat.innerHTML = "";
    state.messages.forEach((m) => addMessage(m.role, m.content));
  }
  renderState(state);
}

async function loadHistory() {
  const data = await apiRequest("/api/history");
  renderHistory(data.history || []);
}

async function apiRequest(url, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${url}`, options);
  } catch (error) {
    throw new Error("The local server is not running. Start it with: python web_app.py");
  }

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : { error: await response.text() };

  if (!response.ok) {
    throw new Error(payload.error || `Request failed (HTTP ${response.status}).`);
  }
  return payload;
}

// ─── Form Submit ────────────────────────────────────────────

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  addMessage("user", message);
  input.value    = "";
  input.disabled = true;

  setStatus("thinking");
  const typingRow = addTypingIndicator();

  try {
    const data = await apiRequest("/api/chat", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ message }),
    });

    removeTypingIndicator();
    addMessage("assistant", data.answer);
    renderState(data);
    setStatus("ready");
  } catch (error) {
    removeTypingIndicator();
    addMessage("assistant", `Sorry, ${error.message}`);
    setStatus("error");
  } finally {
    input.disabled = false;
    input.focus();
  }
});

// ─── Suggestion Chips ───────────────────────────────────────

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.dataset.prompt;
    form.requestSubmit();
  });
});

// ─── Reset Button ───────────────────────────────────────────

document.querySelector("#reset-button").addEventListener("click", async () => {
  if (!confirm("Start a new bill and clear this conversation?")) return;
  try {
    await apiRequest("/api/reset", { method: "POST" });
    chat.innerHTML = "";
    addMessage("assistant", "Fresh bill started. Tell me who paid and how much.");
    await loadState();
    await loadHistory();
    setStatus("ready");
  } catch (error) {
    addMessage("assistant", `Sorry, ${error.message}`);
    setStatus("error");
  }
});

// ─── Init ───────────────────────────────────────────────────

Promise.all([loadState(), loadHistory()]).catch((error) => {
  addMessage("assistant", `Sorry, ${error.message}`);
  setStatus("error");
});
