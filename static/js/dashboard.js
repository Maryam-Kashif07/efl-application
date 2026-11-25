function addRow(body, values) {
  const tr = document.createElement("tr");
  for (const text of values) {
    const td = document.createElement("td");
    td.textContent = text;
    tr.appendChild(td);
  }
  body.appendChild(tr);
}

async function loadDashboard() {
  try {
    const reply = await getJson("/api/dashboard");
    if (!reply.ok) {
      return;
    }
    const d = reply.data;
    const firstName = d.name ? d.name.split(" ")[0] : "";
    showMessage("welcome", firstName ? "Welcome back, " + firstName : "Welcome back");
    const last = d.recent[0];
    showMessage("tile-last", last ? formatMoney(last.amount, last.from_currency) + " → " + formatMoney(last.converted_amount, last.to_currency) : "No conversions yet");
    showMessage("tile-quotes", String(d.saved_quotes));
    showMessage("tile-plan", d.recommended_plan || "No quote yet");
    const body = document.querySelector("#activity-table tbody");
    for (const t of d.recent) {
      addRow(body, [t.created_at.slice(0, 16), "Converted " + formatMoney(t.amount, t.from_currency) + " to " + t.to_currency, formatMoney(t.converted_amount, t.to_currency)]);
    }
    document.getElementById("no-activity").hidden = d.recent.length > 0;
  } catch (problem) {
    showMessage("error", "Could not load your dashboard. Please try again.");
  }
}

loadDashboard();
