const BASE = "/api/v1";
const $ = (sel) => document.querySelector(sel);

function setToken(t) {
  localStorage.setItem("imagelab_token", t || "");
  const el = $("#tokenPreview");
  if (el) el.textContent = t ? t.slice(0, 18) + "…" : "—";
}
function getToken() {
  return localStorage.getItem("imagelab_token") || "";
}
setToken(getToken()); // update navbar token preview on load

const logoutBtn = $("#logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", () => {
    setToken("");
    alert("Logged out");
    window.location.href = "/login";
  });
}

async function api(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  if (!(opts.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  const token = getToken();
  if (token) headers.set("Authorization", "Bearer " + token);

  const res = await fetch(BASE + path, { ...opts, headers });
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    try {
      const j = await res.json();
      if (j.error) msg += ` - ${j.error}`;
    } catch {}
    throw new Error(msg);
  }
  if (res.headers.get("content-type")?.includes("application/json")) {
    return res.json();
  }
  return res;
}
