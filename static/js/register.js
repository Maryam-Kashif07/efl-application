async function register(event) {
  event.preventDefault();
  showMessage("error", "");
  try {
    const reply = await postJson("/api/register", {
      name: document.getElementById("reg-name").value,
      email: document.getElementById("reg-email").value,
      phone: document.getElementById("reg-phone").value,
      password: document.getElementById("reg-password").value,
    });
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      return;
    }
    window.location.href = nextPage() || "/dashboard";
  } catch (problem) {
    showMessage("error", "Could not reach the server. Please try again.");
  }
}

document.getElementById("register-form").addEventListener("submit", register);
document.getElementById("login-link").href = "/login" + window.location.search;
if (nextPage()) {
  document.getElementById("next-note").hidden = false;
}
