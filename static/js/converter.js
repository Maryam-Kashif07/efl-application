async function loadCurrencies() {
  const reply = await getJson("/api/currencies");
  if (!reply.ok) {
    return;
  }
  for (const select of document.querySelectorAll(".currency-list")) {
    for (const item of reply.data) {
      const option = document.createElement("option");
      option.value = item.code;
      option.textContent = item.code + " - " + item.name;
      select.appendChild(option);
    }
  }
  document.getElementById("from").value = "GBP";
  document.getElementById("to").value = "USD";
}

function resetResult() {
  showMessage("error", "");
  showMessage("warning", "");
  document.getElementById("amount").classList.remove("invalid");
  document.getElementById("result-card").hidden = true;
  document.getElementById("placeholder").hidden = false;
  for (const row of document.querySelectorAll("#fee-table tr[data-fee]")) {
    row.classList.remove("highlight");
  }
}

function showResult(d) {
  showMessage("result-from", formatMoney(d.amount, d.from) + " converts to");
  showMessage("result-to", formatMoney(d.converted, d.to));
  showMessage("result-rate", d.rate);
  showMessage("result-percent", d.fee_percent);
  showMessage("result-fee", formatMoney(d.fee_usd, "USD") + " (" + formatMoney(d.fee_original, d.from) + ")");
  showMessage("result-total", formatMoney(d.total_cost_usd, "USD"));
  showMessage("result-updated", "Rates last updated " + formatUtc(d.rates_updated) + " · " + (d.rate_source === "live" ? "live rates" : "saved rates"));
  document.getElementById("placeholder").hidden = true;
  document.getElementById("result-card").hidden = false;
  for (const row of document.querySelectorAll("#fee-table tr[data-fee]")) {
    row.classList.toggle("highlight", Number(row.dataset.fee) === Number(d.fee_percent));
  }
}

async function handleConvert(event) {
  event.preventDefault();
  resetResult();
  const body = {
    amount: document.getElementById("amount").value,
    from: document.getElementById("from").value,
    to: document.getElementById("to").value,
  };
  cacheForm("converter", body);
  try {
    const reply = await postJson("/api/convert", body);
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      if (/amount|decimal/i.test(reply.data.error)) {
        document.getElementById("amount").classList.add("invalid");
      }
      return;
    }
    showResult(reply.data);
    if (reply.data.warning) {
      showMessage("warning", reply.data.warning);
    }
    clearCachedForm("converter");
  } catch (problem) {
    showMessage("error", "Could not reach the server. Your entries are saved on this device; try again shortly.");
  }
}

async function startConverter() {
  await loadCurrencies();
  const saved = restoreForm("converter");
  if (saved) {
    document.getElementById("amount").value = saved.amount;
    document.getElementById("from").value = saved.from;
    document.getElementById("to").value = saved.to;
  }
  const amountBox = document.getElementById("amount");
  amountBox.addEventListener("blur", () => {
    const text = amountBox.value.trim();
    if (/^\d+(\.\d{1,2})?$/.test(text)) {
      amountBox.value = Number(text).toFixed(2);
    }
  });
  document.getElementById("convert-form").addEventListener("submit", handleConvert);
}

startConverter();
