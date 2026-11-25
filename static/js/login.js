const LOCK_MILLISECONDS = 300000;

async function logIn(event) {
  event.preventDefault();
  showMessage("error", "");
  const button = document.getElementById("login-button");
  try {
    const reply = await postJson("/api/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      if (reply.status === 429) {
        button.disabled = true;
        setTimeout(() => { button.disabled = false; }, LOCK_MILLISECONDS);
      }
      return;
    }
    window.location.href = nextPage() || "/dashboard";
  } catch (problem) {
    showMessage("error", "Could not reach the server. Please try again.");
  }
}

document.getElementById("login-form").addEventListener("submit", logIn);
document.getElementById("register-link").href = "/register" + window.location.search;

const params = new URLSearchParams(window.location.search);
if (params.get("reset") === "1") {
  document.getElementById("reset-note").hidden = false;
} else if (params.get("expired") === "1") {
  document.getElementById("expired-note").hidden = false;
} else if (nextPage()) {
  document.getElementById("next-note").hidden = false;
}
