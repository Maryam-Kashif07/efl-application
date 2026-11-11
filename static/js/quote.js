// Quote page.
let currentQuoteId = null;                                              // The id of the quote on screen, used by the Save button

function addCell(row, text) {                                           // Add one table cell to a row
  const cell = document.createElement("td");                            // Make a cell
  cell.textContent = text;                                              // Plain text only, so nothing can inject HTML
  row.appendChild(cell);                                                // Put it in the row
}                                                                       // End of addCell

function fillQuoteTable(rows) {                                         // Show the chosen plan's six result rows
  const body = document.querySelector("#quote-table tbody");            // Find the table body
  body.replaceChildren();                                               // Remove old rows
  for (const r of rows) {                                               // One table row per result
    const tr = document.createElement("tr");                            // Make a row
    addCell(tr, r.years);                                               // Years
    addCell(tr, r.scenario === "min" ? "Minimum return" : "Maximum return");  // Scenario in words
    addCell(tr, formatMoney(r.contributed, "GBP"));                     // Money paid in
    addCell(tr, formatMoney(r.final_value, "GBP"));                     // Final value
    addCell(tr, formatMoney(r.total_profit, "GBP"));                    // Profit
    addCell(tr, formatMoney(r.total_fees, "GBP"));                      // Fees
    addCell(tr, formatMoney(r.total_tax, "GBP"));                       // Tax
    body.appendChild(tr);                                               // Add the row to the table
  }                                                                     // End of the loop
}                                                                       // End of fillQuoteTable

function fillCompareTable(plans, recommendedId) {                       // Show every plan side by side
  const body = document.querySelector("#compare-table tbody");          // Find the table body
  body.replaceChildren();                                               // Remove old rows
  for (const plan of plans) {                                           // One row per plan
    const tr = document.createElement("tr");                            // Make a row
    addCell(tr, plan.name + (plan.plan_id === recommendedId ? " (recommended)" : ""));  // Name, with a tag on the best plan
    addCell(tr, plan.eligible ? "Yes" : "No: " + plan.reasons.join(" "));  // Yes, or the reasons it is not available
    const best = plan.results.find(r => r.scenario === "max" && r.years === 10);  // The 10-year best-case row, if the plan is available
    addCell(tr, best ? formatMoney(best.final_value, "GBP") : "-");     // Its value, or a dash
    body.appendChild(tr);                                               // Add the row to the table
  }                                                                     // End of the loop
}                                                                       // End of fillCompareTable

function makeSvg(name, attributes) {                                    // Create one SVG element with its attributes
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);  // SVG elements need this special namespace
  for (const key in attributes) {                                       // Each attribute
    element.setAttribute(key, attributes[key]);                         // Set it
  }                                                                     // End of the loop
  return element;                                                       // Give the element back
}                                                                       // End of makeSvg

function drawChart(rows) {                                              // Draw the bar chart: minimum and maximum final value for each time frame
  const svg = document.getElementById("quote-chart");                   // Find the drawing area
  svg.replaceChildren();                                                // Clear the old chart
  const biggest = Math.max(1, ...rows.map(r => Number(r.final_value)));  // The tallest bar sets the scale
  [1, 5, 10].forEach((year, i) => {                                     // One group of two bars for each time frame
    ["min", "max"].forEach((scenario, j) => {                           // Minimum bar, then maximum bar
      const row = rows.find(r => r.years === year && r.scenario === scenario);  // The matching result row
      const height = Math.max(0, (Number(row.final_value) / biggest) * 200);  // Bar height in pixels, never below zero
      const x = 70 + i * 170 + j * 60;                                  // Left edge of the bar
      svg.appendChild(makeSvg("rect", { x: x, y: 250 - height, width: 50, height: height, fill: scenario === "min" ? "#0e7490" : "#f59e0b" }));  // The bar; teal for minimum, amber for maximum
      const label = makeSvg("text", { x: x + 25, y: 244 - height, "text-anchor": "middle", "font-size": 11 });  // A value label above the bar
      label.textContent = Math.round(Number(row.final_value)).toLocaleString("en-GB");  // Whole pounds keep the label short
      svg.appendChild(label);                                           // Add the label
    });                                                                 // End of the scenario loop
    const axis = makeSvg("text", { x: 70 + i * 170 + 55, y: 272, "text-anchor": "middle", "font-size": 13 });  // The time-frame label under the bars
    axis.textContent = year + (year === 1 ? " year" : " years");        // Text such as 5 years
    svg.appendChild(axis);                                              // Add it
  });                                                                   // End of the time-frame loop
  svg.appendChild(makeSvg("rect", { x: 70, y: 285, width: 10, height: 10, fill: "#0e7490" }));  // Legend square for minimum
  const minText = makeSvg("text", { x: 85, y: 294, "font-size": 11 });  // Legend text for minimum
  minText.textContent = "Minimum return";                               // The words
  svg.appendChild(minText);                                             // Add it
  svg.appendChild(makeSvg("rect", { x: 200, y: 285, width: 10, height: 10, fill: "#f59e0b" }));  // Legend square for maximum
  const maxText = makeSvg("text", { x: 215, y: 294, "font-size": 11 });  // Legend text for maximum
  maxText.textContent = "Maximum return";                               // The words
  svg.appendChild(maxText);                                             // Add it
}                                                                       // End of drawChart

async function handleQuote(event) {                                     // Runs when the form is sent
  event.preventDefault();                                               // Stop the page reloading
  showMessage("error", "");                                             // Clear the old error
  showMessage("save-message", "");                                      // Clear the old save message
  document.getElementById("quote-output").hidden = true;                // Hide old results
  const body = {                                                        // The data we send
    lump_sum: document.getElementById("lump").value,                    // Lump sum as typed
    monthly: document.getElementById("monthly").value,                  // Monthly amount as typed
    plan_id: document.getElementById("plan").value,                     // Chosen plan id
  };                                                                    // End of the data
  cacheForm("quote", body);                                             // Cache the entries immediately
  try {                                                                 // Catch network problems
    const reply = await postJson("/api/quote", body);                   // Send the request
    if (!reply.ok) {                                                    // A 400 or other error
      showMessage("error", reply.data.error);                           // Show the message
      return;                                                           // Stop here
    }                                                                   // End of the error case
    const d = reply.data;                                               // Shorter name
    currentQuoteId = d.quote_id;                                        // Remember the quote for the Save button
    const chosen = d.plans.find(p => p.plan_id === d.chosen_plan_id);   // The plan the user picked
    fillQuoteTable(chosen.results);                                     // Fill the numbers
    drawChart(chosen.results);                                          // Draw the chart
    fillCompareTable(d.plans, d.recommended_plan_id);                   // Fill the comparison
    const best = d.plans.find(p => p.plan_id === d.recommended_plan_id);  // The recommended plan, if there is one
    showMessage("recommendation", best ? "Recommended: " + best.name + " (highest value after 10 years in the best case, after fees and tax)." : "No plan is available for these amounts.");  // Say which plan is best
    const hasLoss = chosen.results.some(r => r.loss);                   // Does any result lose money?
    showMessage("loss-warning", hasLoss ? "Warning: in some cases the monthly fees are larger than the returns, so you would get back less than you pay in." : "");  // Warn the user plainly
    document.getElementById("quote-output").hidden = false;             // Show the results
    clearCachedForm("quote");                                           // It worked, so clear the cache
  } catch (problem) {                                                   // The request itself failed
    showMessage("error", "Could not reach the server. Your entries are saved on this device; try again shortly.");  // Nothing is lost
  }                                                                     // End of try/catch
}                                                                       // End of handleQuote

async function handleSave() {                                           // Runs when Save is pressed
  if (currentQuoteId === null) {                                        // No quote on screen
    return;                                                             // Nothing to save
  }                                                                     // End of the check
  const reply = await postJson("/api/quotes/" + currentQuoteId + "/save", {});  // Ask the server to mark it saved
  showMessage("save-message", reply.ok ? "Quote saved. You can find it in History." : reply.data.error);  // Confirm or show the error
}                                                                       // End of handleSave

function startQuote() {                                                 // Set the page up
  document.getElementById("quote-form").addEventListener("submit", handleQuote);  // Form sent: get a quote
  document.getElementById("save-quote").addEventListener("click", handleSave);  // Button pressed: save
  for (const id of ["lump", "monthly"]) {                               // Both money boxes
    document.getElementById(id).addEventListener("blur", () => {        // When the user leaves the box
      const value = Number(document.getElementById(id).value);          // Read the number
      if (document.getElementById(id).value.trim() !== "" && !Number.isNaN(value)) {  // Only tidy a valid number
        document.getElementById(id).value = value.toFixed(2);           // Show it with two decimal places
      }                                                                 // End of the check
    });                                                                 // End of the blur handler
  }                                                                     // End of the loop
  const saved = restoreForm("quote");                                   // Was something cached last time?
  if (saved) {                                                          // Yes: put it back
    document.getElementById("lump").value = saved.lump_sum;             // Restore the lump sum
    document.getElementById("monthly").value = saved.monthly;           // Restore the monthly amount
    document.getElementById("plan").value = saved.plan_id;              // Restore the plan
  }                                                                     // End of the restore
}                                                                       // End of startQuote

startQuote();                                                           // Run it as soon as the page loads