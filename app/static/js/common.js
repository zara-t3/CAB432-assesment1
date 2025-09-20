const BASE = "/api/v1";
const $ = (sel) => document.querySelector(sel);

function setToken(t) {
  localStorage.setItem("imagelab_token", t || "");
  updateNavbarAuth();
}

function getToken() {
  return localStorage.getItem("imagelab_token") || "";
}


function logout() {
  setToken("");
  alert("Logged out");
  window.location.href = "/login";
}

function updateNavbarAuth() {
  const loginBtn = $("#loginBtn");
  const profileSection = $("#profileSection");
  const hasToken = !!getToken();

  if (loginBtn && profileSection) {
    if (hasToken) {
      loginBtn.classList.add("d-none");
      profileSection.classList.remove("d-none");
    } else {
      loginBtn.classList.remove("d-none");
      profileSection.classList.add("d-none");
    }
  }
}

const logoutBtn = $("#logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", logout);
}


document.addEventListener("DOMContentLoaded", updateNavbarAuth);

async function api(path, opts = {}) {
  const headers = new Headers(opts.headers || {});
  if (!(opts.body instanceof FormData)) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");

  const token = getToken();
  if (token) headers.set("Authorization", "Bearer " + token); 

  const res = await fetch(BASE + path, { ...opts, headers });
  const isJson = res.headers.get("content-type")?.includes("application/json");
  if (!res.ok) {
    let msg = `${res.status} ${res.statusText}`;
    if (isJson) {
      const body = await res.json().catch(() => null);
      if (body) msg += ` - ${JSON.stringify(body)}`;
    }
    throw new Error(msg);
  }
  return isJson ? res.json() : res;
}
