let currentQuoteId = null;

function addCell(row, text, className) {
  const cell = document.createElement("td");
  cell.textContent = text;
  if (className) {
    cell.className = className;
  }
  row.appendChild(cell);
}

function fillQuoteTable(rows) {
  const body = document.querySelector("#quote-table tbody");
  body.replaceChildren();
  for (const r of rows) {
    const tr = document.createElement("tr");
    addCell(tr, r.years);
    addCell(tr, r.scenario === "min" ? "Minimum" : "Maximum");
    addCell(tr, formatMoney(r.contributed, "GBP"));
    addCell(tr, formatMoney(r.final_value, "GBP"));
    addCell(tr, formatMoney(r.total_profit, "GBP"), Number(r.total_profit) < 0 ? "negative" : "positive");
    addCell(tr, formatMoney(r.total_fees, "GBP"));
    addCell(tr, formatMoney(r.total_tax, "GBP"));
    body.appendChild(tr);
  }
}

function fillCompareTable(plans, recommendedId) {
  const body = document.querySelector("#compare-table tbody");
  body.replaceChildren();
  for (const plan of plans) {
    const tr = document.createElement("tr");
    addCell(tr, plan.name + (plan.plan_id === recommendedId ? " (recommended)" : ""));
    addCell(tr, plan.eligible ? "Yes" : "No: " + plan.reasons.join(" "));
    const best = plan.results.find(r => r.scenario === "max" && r.years === 10);
    addCell(tr, best ? formatMoney(best.final_value, "GBP") : "-");
    body.appendChild(tr);
  }
}

function makeSvg(name, attributes) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const key in attributes) {
    element.setAttribute(key, attributes[key]);
  }
  return element;
}

function drawChart(rows) {
  const svg = document.getElementById("quote-chart");
  svg.replaceChildren();
  const biggest = Math.max(1, ...rows.map(r => Number(r.final_value)));
  [1, 5, 10].forEach((year, i) => {
    ["min", "max"].forEach((scenario, j) => {
      const row = rows.find(r => r.years === year && r.scenario === scenario);
      const height = Math.max(0, (Number(row.final_value) / biggest) * 200);
      const x = 70 + i * 170 + j * 60;
      svg.appendChild(makeSvg("rect", { x: x, y: 250 - height, width: 50, height: height, rx: 6, fill: scenario === "min" ? "#4338ca" : "#f59e0b" }));
      const label = makeSvg("text", { x: x + 25, y: 244 - height, "text-anchor": "middle", "font-size": 11, fill: "#1e1b4b" });
      label.textContent = Math.round(Number(row.final_value)).toLocaleString("en-GB");
      svg.appendChild(label);
    });
    const axis = makeSvg("text", { x: 70 + i * 170 + 55, y: 272, "text-anchor": "middle", "font-size": 13, fill: "#1e1b4b" });
    axis.textContent = year + (year === 1 ? " year" : " years");
    svg.appendChild(axis);
  });
  svg.appendChild(makeSvg("rect", { x: 70, y: 285, width: 10, height: 10, fill: "#4338ca" }));
  const minText = makeSvg("text", { x: 85, y: 294, "font-size": 11, fill: "#1e1b4b" });
  minText.textContent = "Minimum return";
  svg.appendChild(minText);
  svg.appendChild(makeSvg("rect", { x: 200, y: 285, width: 10, height: 10, fill: "#f59e0b" }));
  const maxText = makeSvg("text", { x: 215, y: 294, "font-size": 11, fill: "#1e1b4b" });
  maxText.textContent = "Maximum return";
  svg.appendChild(maxText);
}

function resetQuote() {
  showMessage("error", "");
  showMessage("save-message", "");
  document.getElementById("quote-output").hidden = true;
  document.getElementById("quote-placeholder").hidden = false;
}

async function handleQuote(event) {
  event.preventDefault();
  resetQuote();
  const body = {
    lump_sum: document.getElementById("lump").value,
    monthly: document.getElementById("monthly").value,
    plan_id: document.getElementById("plan").value,
  };
  cacheForm("quote", body);
  try {
    const reply = await postJson("/api/quote", body);
    if (!reply.ok) {
      showMessage("error", reply.data.error);
      return;
    }
    const d = reply.data;
    currentQuoteId = d.quote_id;
    const chosen = d.plans.find(p => p.plan_id === d.chosen_plan_id);
    fillQuoteTable(chosen.results);
    drawChart(chosen.results);
    fillCompareTable(d.plans, d.recommended_plan_id);
    const best = d.plans.find(p => p.plan_id === d.recommended_plan_id);
    showMessage("recommendation", best ? "Recommended: " + best.name + " (highest value after 10 years in the best case, after fees and tax)." : "No plan is available for these amounts.");
    const hasLoss = chosen.results.some(r => r.loss);
    showMessage("loss-warning", hasLoss ? "Warning: in some cases the monthly fees are larger than the returns, so you would get back less than you pay in." : "");
    document.getElementById("quote-placeholder").hidden = true;
    document.getElementById("quote-output").hidden = false;
    clearCachedForm("quote");
  } catch (problem) {
    showMessage("error", "Could not reach the server. Your entries are saved on this device; try again shortly.");
  }
}

async function handleSave() {
  if (currentQuoteId === null) {
    return;
  }
  const reply = await postJson("/api/quotes/" + currentQuoteId + "/save", {});
  showMessage("save-message", reply.ok ? "Quote saved. You can find it in History." : reply.data.error);
}

function startQuote() {
  document.getElementById("quote-form").addEventListener("submit", handleQuote);
  document.getElementById("save-quote").addEventListener("click", handleSave);
  for (const id of ["lump", "monthly"]) {
    document.getElementById(id).addEventListener("blur", () => {
      const value = Number(document.getElementById(id).value);
      if (document.getElementById(id).value.trim() !== "" && !Number.isNaN(value)) {
        document.getElementById(id).value = value.toFixed(2);
      }
    });
  }
  const saved = restoreForm("quote");
  if (saved) {
    document.getElementById("lump").value = saved.lump_sum;
    document.getElementById("monthly").value = saved.monthly;
    document.getElementById("plan").value = saved.plan_id;
  }
}

startQuote();
