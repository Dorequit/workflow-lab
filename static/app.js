"use strict";

const $ = (selector) => document.querySelector(selector);
const form = $("#incident-form");
const scenarios = $("#scenario-list");
let examples = [];

function setText(selector, value) { $(selector).textContent = value; }

function appendItem(parent, tag, value, className = "") {
  const item = document.createElement(tag);
  item.textContent = value;
  if (className) item.className = className;
  parent.appendChild(item);
  return item;
}

function loadIncident(incident, id) {
  $("#title").value = incident.title;
  $("#service").value = incident.service;
  $("#environment").value = incident.environment;
  $("#error-rate").value = incident.error_rate_percent;
  $("#affected-users").value = incident.affected_users;
  $("#customer-impact").checked = incident.customer_impact;
  $("#symptoms").value = incident.symptoms.join("\n");
  $("#requested-action").value = incident.requested_action;
  $("#simulate-failure").checked = incident.simulate_tool_failure;
  document.querySelectorAll(".scenario-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.id === id);
    button.setAttribute("aria-pressed", button.dataset.id === id ? "true" : "false");
  });
}

function getIncident() {
  return {
    title: $("#title").value,
    service: $("#service").value,
    environment: $("#environment").value,
    error_rate_percent: Number($("#error-rate").value),
    affected_users: Number($("#affected-users").value),
    customer_impact: $("#customer-impact").checked,
    symptoms: $("#symptoms").value.split("\n").map((item) => item.trim()).filter(Boolean),
    requested_action: $("#requested-action").value,
    simulate_tool_failure: $("#simulate-failure").checked,
  };
}

function renderResult(data) {
  $("#empty-state").hidden = true;
  $("#result").hidden = false;
  const severity = $("#severity");
  severity.textContent = data.severity;
  severity.className = `sev ${data.severity.toLowerCase()}`;
  setText("#severity-tag", data.severity === "SEV1" ? "CRITICAL" : data.severity === "SEV2" ? "HIGH" : data.severity === "SEV3" ? "MODERATE" : "LOW");
  setText("#rationale", data.rationale);
  setText("#owner", data.owner);
  const gate = $("#gate");
  gate.textContent = data.action_gate.status.replaceAll("_", " ");
  gate.className = `gate-${data.action_gate.status}`;
  gate.title = data.action_gate.reason;

  const evidence = $("#evidence");
  evidence.replaceChildren();
  data.evidence.forEach((item) => appendItem(evidence, "li", item));

  const actions = $("#actions");
  actions.replaceChildren();
  data.recommended_actions.forEach((item) => appendItem(actions, "li", item));

  setText("#runbook-title", data.runbook.title);
  setText("#runbook-note", data.runbook.first_step);
  setText("#trace-count", `${data.trace.length} EVENTS`);
  const trace = $("#trace");
  trace.replaceChildren();
  data.trace.forEach((event) => {
    const row = document.createElement("li");
    row.className = `trace-${event.status}`;
    const heading = document.createElement("div");
    appendItem(heading, "strong", event.step);
    appendItem(heading, "span", event.status.toUpperCase(), "trace-status");
    row.appendChild(heading);
    appendItem(row, "p", `${event.detail} · attempt ${event.attempt}`);
    trace.appendChild(row);
  });
}

async function runIncident(event) {
  if (event) event.preventDefault();
  if (!form.reportValidity()) return;
  const error = $("#form-error");
  error.hidden = true;
  const button = $("#run-button");
  button.disabled = true;
  button.textContent = "Running…";
  try {
    const response = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(getIncident()),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Could not run workflow");
    renderResult(data);
  } catch (cause) {
    error.textContent = cause.message;
    error.hidden = false;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Run workflow <span aria-hidden="true">↗</span>';
  }
}

async function main() {
  try {
    const response = await fetch("/api/examples");
    if (!response.ok) throw new Error("Examples are unavailable");
    examples = await response.json();
    examples.forEach((example, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "scenario-button";
      button.dataset.id = example.id;
      button.setAttribute("aria-pressed", "false");
      appendItem(button, "span", `0${index + 1}`);
      appendItem(button, "strong", example.label);
      button.addEventListener("click", () => { loadIncident(example.incident, example.id); runIncident(); });
      scenarios.appendChild(button);
    });
    if (examples.length) { loadIncident(examples[0].incident, examples[0].id); await runIncident(); }
  } catch (cause) {
    const error = $("#form-error");
    error.textContent = cause.message;
    error.hidden = false;
  }
}

form.addEventListener("submit", runIncident);
form.addEventListener("input", () => { document.querySelectorAll(".scenario-button").forEach((button) => { button.classList.remove("active"); button.setAttribute("aria-pressed", "false"); }); });
main();
