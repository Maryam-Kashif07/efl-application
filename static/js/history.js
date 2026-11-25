let allTransactions = [];
let allQuotes = [];
let view = "converter";

const converterHeads = ["Date", "From", "To", "Amount", "Fee (USD)", "Received"];
const quoteHeads = ["Date", "Plan", "Lump sum", "Monthly", "Best case after 10 years", "Worst case after 10 years"];

function trashIcon() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const attributes = { viewBox: "0 0 24 24", width: "18", height: "18", fill: "none", stroke: "currentColor", "stroke-width": "2", "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true" };
  for (const key in attributes) {
    svg.setAttribute(key, attributes[key]);
  }
  for (const d of ["M3 6h18", "M8 6V4h8v2", "M19 6l-1 14H6L5 6", "M10 11v6", "M14 11v6"]) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", d);
    svg.appendChild(path);
  }
  return svg;
}

function addCells(row, values) {
  for (const text of values) {
    const td = document.createElement("td");
    td.textContent = text;
    row.appendChild(td);
  }
}

async function deleteTransaction(t, button) {
  if (!window.confirm("Delete this conversion from your history?")) {
    return;
  }
  showMessage("error", "");
  showMessage("history-message", "");
  button.disabled = true;
  try {
    const reply = await deleteJson("/api/transactions/" + t.transaction_id);
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      button.disabled = false;
      return;
    }
    allTransactions = allTransactions.filter(x => x.transaction_id !== t.transaction_id);
    showTiles();
    showRows();
    showMessage("history-message", "Conversion deleted.");
  } catch (problem) {
    showMessage("error", "Could not delete the conversion. Please try again.");
    button.disabled = false;
  }
}

function addTransactionRow(body, t) {
  const tr = document.createElement("tr");
  addCells(tr, [t.created_at.slice(0, 16), t.from_currency, t.to_currency, formatMoney(t.amount, t.from_currency), formatMoney(t.fee_usd, "USD"), formatMoney(t.converted_amount, t.to_currency)]);
  const cell = document.createElement("td");
  cell.className = "actions-cell";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "icon-button";
  button.title = "Delete";
  button.setAttribute("aria-label", "Delete the conversion of " + formatMoney(t.amount, t.from_currency) + " on " + t.created_at.slice(0, 16));
  button.appendChild(trashIcon());
  button.addEventListener("click", () => deleteTransaction(t, button));
  cell.appendChild(button);
  tr.appendChild(cell);
  body.appendChild(tr);
}

function addQuoteRow(body, q) {
  const best = q.results.find(r => r.scenario === "max" && r.years === 10);
  const worst = q.results.find(r => r.scenario === "min" && r.years === 10);
  const tr = document.createElement("tr");
  addCells(tr, [q.created_at.slice(0, 16), q.plan_name, formatMoney(q.lump_sum, "GBP"), formatMoney(q.monthly_amount, "GBP"), formatMoney(best.final_value, "GBP"), formatMoney(worst.final_value, "GBP")]);
  body.appendChild(tr);
}

function withinDays(createdAt, days) {
  if (!days) {
    return true;
  }
  const time = new Date(createdAt.replace(" ", "T") + "Z").getTime();
  return Date.now() - time <= Number(days) * 86400000;
}

function sortRows(rows, how, idOf, amountOf) {
  const copy = rows.slice();
  if (how === "oldest") {
    return copy.sort((a, b) => idOf(a) - idOf(b));
  }
  if (how === "largest") {
    return copy.sort((a, b) => amountOf(b) - amountOf(a));
  }
  if (how === "smallest") {
    return copy.sort((a, b) => amountOf(a) - amountOf(b));
  }
  return copy.sort((a, b) => idOf(b) - idOf(a));
}

function showHead(titles, withDelete) {
  const row = document.createElement("tr");
  for (const title of titles) {
    const th = document.createElement("th");
    th.textContent = title;
    row.appendChild(th);
  }
  if (withDelete) {
    const th = document.createElement("th");
    const hidden = document.createElement("span");
    hidden.className = "visually-hidden";
    hidden.textContent = "Delete";
    th.appendChild(hidden);
    row.appendChild(th);
  }
  document.querySelector("#history-table thead").replaceChildren(row);
}

function showTiles() {
  let totalFees = 0;
  for (const t of allTransactions) {
    totalFees += Number(t.fee_usd);
  }
  showMessage("tile-count", String(allTransactions.length));
  showMessage("tile-fees", formatMoney(totalFees, "USD"));
  showMessage("tile-quotes", String(allQuotes.length));
}

function showRows() {
  const days = document.getElementById("filter-dates").value;
  const how = document.getElementById("filter-sort").value;
  const body = document.querySelector("#history-table tbody");
  body.replaceChildren();
  let count = 0;
  if (view === "converter") {
    const currencyCode = document.getElementById("filter-currency").value;
    const rows = sortRows(allTransactions.filter(t =>
      (!currencyCode || t.from_currency === currencyCode || t.to_currency === currencyCode) && withinDays(t.created_at, days)
    ), how, t => t.transaction_id, t => Number(t.amount));
    showHead(converterHeads, true);
    for (const t of rows) {
      addTransactionRow(body, t);
    }
    count = rows.length;
    showMessage("no-rows", "No conversions to show.");
  } else {
    const rows = sortRows(allQuotes.filter(q => withinDays(q.created_at, days)), how, q => q.quote_id, q => Number(q.lump_sum));
    showHead(quoteHeads, false);
    for (const q of rows) {
      addQuoteRow(body, q);
    }
    count = rows.length;
    showMessage("no-rows", "No saved quotes to show.");
  }
  document.getElementById("no-rows").hidden = count > 0;
}

function setView(name) {
  view = name;
  for (const id of ["converter", "quote"]) {
    const tab = document.getElementById("tab-" + id);
    tab.classList.toggle("active", id === name);
    tab.setAttribute("aria-pressed", id === name ? "true" : "false");
  }
  document.getElementById("currency-filter").hidden = name !== "converter";
  document.getElementById("table-scroll").scrollTop = 0;
  showRows();
}

async function loadCurrencyFilter() {
  const reply = await getJson("/api/currencies");
  if (!reply.ok) {
    return;
  }
  const select = document.getElementById("filter-currency");
  for (const item of reply.data) {
    const option = document.createElement("option");
    option.value = item.code;
    option.textContent = item.code;
    select.appendChild(option);
  }
}

async function loadHistory() {
  try {
    await loadCurrencyFilter();
    const reply = await getJson("/api/history");
    if (!reply.ok) {
      return;
    }
    allTransactions = reply.data.transactions;
    allQuotes = reply.data.quotes;
    showTiles();
    showRows();
  } catch (problem) {
    showMessage("error", "Could not load your history. Please try again.");
  }
}

for (const id of ["filter-currency", "filter-dates", "filter-sort"]) {
  document.getElementById(id).addEventListener("change", showRows);
}
document.getElementById("tab-converter").addEventListener("click", () => setView("converter"));
document.getElementById("tab-quote").addEventListener("click", () => setView("quote"));
showHead(converterHeads, true);
loadHistory();
