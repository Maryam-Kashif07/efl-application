function showMessage(id, text) {
  document.getElementById(id).textContent = text;
}

function formatMoney(value, code) {
  return Number(value).toLocaleString("en-GB", { style: "currency", currency: code, currencyDisplay: "narrowSymbol", minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatUtc(text) {
  if (!text) {
    return "unknown";
  }
  const date = new Date(text.replace(" ", "T") + "Z");
  return date.toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC" }) + " UTC";
}

function nextPage() {
  const next = new URLSearchParams(window.location.search).get("next");
  if (next && next.startsWith("/") && !next.startsWith("//") && !next.includes("\\")) {
    return next;
  }
  return null;
}

function goToLogin(data) {
  const expired = data && data.expired ? "&expired=1" : "";
  window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname) + expired;
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (response.status === 401 && window.location.pathname !== "/login") {
    goToLogin(data);
  }
  return { ok: response.ok, status: response.status, data: data };
}

async function getJson(url) {
  const response = await fetch(url);
  const data = await response.json();
  if (response.status === 401) {
    goToLogin(data);
  }
  return { ok: response.ok, status: response.status, data: data };
}

async function deleteJson(url) {
  const response = await fetch(url, { method: "DELETE" });
  const data = await response.json();
  if (response.status === 401) {
    goToLogin(data);
  }
  return { ok: response.ok, status: response.status, data: data };
}

function cacheForm(name, values) {
  try {
    localStorage.setItem("efl-" + name, JSON.stringify(values));
  } catch (problem) {
    console.warn("Could not cache the form", problem);
  }
}

function restoreForm(name) {
  try {
    const text = localStorage.getItem("efl-" + name);
    return text ? JSON.parse(text) : null;
  } catch (problem) {
    return null;
  }
}

function clearCachedForm(name) {
  try {
    localStorage.removeItem("efl-" + name);
  } catch (problem) {
    console.warn("Could not clear the cache", problem);
  }
}

const logoutLink = document.getElementById("logout-link");
if (logoutLink) {
  logoutLink.addEventListener("click", async (event) => {
    event.preventDefault();
    await postJson("/api/logout", {});
    window.location.href = "/";
  });
}
