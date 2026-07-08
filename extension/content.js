function textOf(selector) {
  const el = document.querySelector(selector);
  return el ? el.textContent.trim() : "";
}

function scrapeLinkedIn() {
  return {
    job_title: textOf("h1"),
    company: textOf(".job-details-jobs-unified-top-card__company-name"),
    job_description: textOf("#job-details"),
  };
}

function scrapeGreenhouse() {
  return {
    job_title: textOf("h1.app-title"),
    company: textOf(".company-name"),
    job_description: textOf("#content"),
  };
}

function scrapeLever() {
  return {
    job_title: textOf("h2"),
    company: textOf(".main-header-text"),
    job_description: textOf(".section-wrapper"),
  };
}

function scrapeJobData() {
  const host = window.location.hostname;

  if (host.includes("linkedin.com")) {
    return scrapeLinkedIn();
  }
  if (host.includes("greenhouse.io")) {
    return scrapeGreenhouse();
  }
  if (host.includes("lever.co")) {
    return scrapeLever();
  }

  return { job_title: "", company: "", job_description: "" };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message && message.type === "SCRAPE_JOB_DATA") {
    sendResponse(scrapeJobData());
  }
  return true;
});
