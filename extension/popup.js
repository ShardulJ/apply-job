const API_URL = "http://localhost:8000/analyze";

const analyzeBtn = document.getElementById("analyzeBtn");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error");
const resultsEl = document.getElementById("results");
const scoreBadgeEl = document.getElementById("scoreBadge");
const decisionTextEl = document.getElementById("decisionText");
const bulletsListEl = document.getElementById("bulletsList");
const bulletsSectionEl = document.getElementById("bulletsSection");
const violationsListEl = document.getElementById("violationsList");
const violationsSectionEl = document.getElementById("violationsSection");

function setHidden(el, hidden) {
  el.classList.toggle("hidden", hidden);
}

function showError(message) {
  errorEl.textContent = message;
  setHidden(errorEl, false);
  setHidden(resultsEl, true);
}

function resetView() {
  setHidden(errorEl, true);
  setHidden(resultsEl, true);
  errorEl.textContent = "";
}

function getActiveTab() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError || !tabs.length) {
        reject(new Error("Could not find the active tab."));
        return;
      }
      resolve(tabs[0]);
    });
  });
}

function scrapeJobData(tabId) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type: "SCRAPE_JOB_DATA" }, (response) => {
      if (chrome.runtime.lastError) {
        reject(
          new Error(
            "Could not read this page. Open a job posting on LinkedIn, Greenhouse, or Lever, then try again."
          )
        );
        return;
      }
      if (!response || !response.job_description) {
        reject(
          new Error(
            "Could not find a job description on this page. Make sure the full job posting is visible."
          )
        );
        return;
      }
      resolve(response);
    });
  });
}

async function analyzeJob(jobData) {
  let response;
  try {
    response = await fetch(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_description: jobData.job_description,
        company: jobData.company,
        job_title: jobData.job_title,
      }),
    });
  } catch (err) {
    throw new Error(
      "Could not reach the analysis server. Make sure the backend is running on localhost:8000."
    );
  }

  if (!response.ok) {
    throw new Error(`Analysis server returned an error (status ${response.status}).`);
  }

  return response.json();
}

function renderResults(result) {
  const score = Number(result.match_score) || 0;
  scoreBadgeEl.textContent = `${score}`;
  scoreBadgeEl.classList.remove("badge-green", "badge-red");
  scoreBadgeEl.classList.add(score > 65 ? "badge-green" : "badge-red");

  const decision = (result.decision || "").toUpperCase();
  decisionTextEl.textContent = decision === "APPLY" ? "APPLY" : decision === "FLAG" ? "FLAG" : "SKIP";
  decisionTextEl.classList.remove("decision-apply", "decision-skip");
  decisionTextEl.classList.add(decision === "APPLY" ? "decision-apply" : "decision-skip");

  bulletsListEl.innerHTML = "";
  const bulletsText = result.tweaked_bullets || "";
  const bulletLines = bulletsText
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  if (bulletLines.length) {
    for (const line of bulletLines) {
      const li = document.createElement("li");
      li.textContent = line;
      bulletsListEl.appendChild(li);
    }
    setHidden(bulletsSectionEl, false);
  } else {
    setHidden(bulletsSectionEl, true);
  }

  violationsListEl.innerHTML = "";
  const violations = result.style_violations || [];
  if (violations.length) {
    for (const violation of violations) {
      const li = document.createElement("li");
      li.textContent = violation;
      violationsListEl.appendChild(li);
    }
    setHidden(violationsSectionEl, false);
  } else {
    setHidden(violationsSectionEl, true);
  }

  setHidden(resultsEl, false);
}

analyzeBtn.addEventListener("click", async () => {
  resetView();
  setHidden(loadingEl, false);
  analyzeBtn.disabled = true;

  try {
    const tab = await getActiveTab();
    const jobData = await scrapeJobData(tab.id);
    const result = await analyzeJob(jobData);
    renderResults(result);
  } catch (err) {
    showError(err.message || "Something went wrong. Please try again.");
  } finally {
    setHidden(loadingEl, true);
    analyzeBtn.disabled = false;
  }
});
