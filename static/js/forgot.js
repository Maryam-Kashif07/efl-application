async function sendLink(event) {
  event.preventDefault();
  showMessage("error", "");
  document.getElementById("forgot-result").hidden = true;
  try {
    const reply = await postJson("/api/forgot-password", { email: document.getElementById("forgot-email").value });
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      return;
    }
    const prefix = window.location.origin + "/reset-password?token=";
    if (reply.data.reset_link && reply.data.reset_link.startsWith(prefix)) {
      window.location.href = reply.data.reset_link;
      return;
    }
    showMessage("forgot-result", reply.data.message);
    document.getElementById("forgot-result").hidden = false;
  } catch (problem) {
    showMessage("error", "Could not reach the server. Please try again.");
  }
}

document.getElementById("forgot-form").addEventListener("submit", sendLink);
