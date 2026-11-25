const token = new URLSearchParams(window.location.search).get("token");

async function resetPassword(event) {
  event.preventDefault();
  showMessage("error", "");
  try {
    const reply = await postJson("/api/reset-password", {
      token: token,
      password: document.getElementById("new-password").value,
      confirm: document.getElementById("confirm-password").value,
    });
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      return;
    }
    window.location.href = "/login?reset=1";
  } catch (problem) {
    showMessage("error", "Could not reach the server. Please try again.");
  }
}

if (!token) {
  showMessage("error", "This reset link is not valid. Please request a new one.");
  document.getElementById("reset-button").disabled = true;
}
document.getElementById("reset-form").addEventListener("submit", resetPassword);
