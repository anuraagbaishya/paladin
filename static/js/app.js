async function loadReports() {
  try {
    const resp = await fetch("/vuln_reports");
    const reports = await resp.json();
    const container = document.getElementById("reports");
    container.innerHTML = "";

    reports.forEach(r => {
      const packageName = r.package;
      const repoName = r.repo;
      if (!packageName) return;

      const safeId = packageName.replace(/\//g, "_");
      const disabled = repoName ? false : true;

      const title = repoName ? repoName.split("/").pop() : packageName.split("/").pop();
      const titleSummary = `${title}: ${r.title || r.cve || ""}`;

      const reportDiv = document.createElement("div");
      reportDiv.className = "report";

      // Header
      const header = document.createElement("div");
      header.className = "report-header";

      const headerLeft = document.createElement("div");
      headerLeft.className = "header-left";
      headerLeft.onclick = () => toggleDetails(safeId);

      const chevron = document.createElement("span");
      chevron.className = "chevron";
      chevron.id = "chevron-" + safeId;
      chevron.textContent = "▶";

      const h2 = document.createElement("h2");
      h2.textContent = titleSummary;

      headerLeft.appendChild(chevron);
      headerLeft.appendChild(h2);

      const scanBtn = document.createElement("button");
      scanBtn.className = "scan-btn";
      scanBtn.textContent = "Scan";
      scanBtn.disabled = disabled;
      scanBtn.onclick = e => { e.stopPropagation(); runScan(repoName, scanBtn); };

      header.appendChild(headerLeft);
      header.appendChild(scanBtn);

      reportDiv.appendChild(header);

      // Details
      const detailsDiv = document.createElement("div");
      detailsDiv.className = "report-details";
      detailsDiv.id = "details-" + safeId;
      detailsDiv.appendChild(buildDetailsDOM(r));

      reportDiv.appendChild(detailsDiv);
      container.appendChild(reportDiv);
    });

  } catch (err) {
    console.error("Error loading reports:", err);
    document.getElementById("reports").textContent = "Failed to load reports.";
  }
}

function buildDetailsDOM(r) {
  const table = document.createElement("table");
  table.className = "details-table";

  function addRow(key, value) {
    if (!value) return;
    const tr = document.createElement("tr");

    const tdKey = document.createElement("td");
    tdKey.className = "highlight-key";
    tdKey.textContent = key;

    const tdValue = document.createElement("td");
    tdValue.className = "highlight-value";
    if (value instanceof HTMLElement) tdValue.appendChild(value);
    else tdValue.textContent = value;

    tr.appendChild(tdKey);
    tr.appendChild(tdValue);
    table.appendChild(tr);
  }

  // Title
  addRow("Title", r.title);

  // Repo / Package
  const repoOrPkg = r.repo || r.package;
  let linkUrl = r.repo ? `https://github.com/${r.repo}` : `https://github.com/${r.package}`;
  const link = document.createElement("a");
  link.href = linkUrl;
  link.target = "_blank";
  link.textContent = repoOrPkg;
  addRow("Repo", link);

  // CVE
  if (r.cve) {
    const cveLink = document.createElement("a");
    cveLink.href = `https://cve.mitre.org/cgi-bin/cvename.cgi?name=${r.cve}`;
    cveLink.target = "_blank";
    cveLink.textContent = r.cve;
    addRow("CVE", cveLink);
  }

  // GHSA
  if (r.ghsa) {
    const ghsaLink = document.createElement("a");
    ghsaLink.href = `https://github.com/advisories/${r.ghsa}`;
    ghsaLink.target = "_blank";
    ghsaLink.textContent = r.ghsa;
    addRow("GHSA", ghsaLink);
  }

  // CWE
  if (r.cwe) {
    const cweMatch = r.cwe.match(/CWE-(\d+)/);
    const cweLink = document.createElement("a");
    cweLink.href = cweMatch ? `https://cwe.mitre.org/data/definitions/${cweMatch[1]}.html` : "#";
    cweLink.target = "_blank";
    cweLink.textContent = r.cwe;
    addRow("CWE", cweLink);
  }

  // Severity / CVSS
  if (r.cvss_score && r.cvss_vector) {
    addRow("Severity", r.severity);
    addRow("CVSS Score", r.cvss_score);
    addRow("CVSS Vector", r.cvss_vector);
  }

  // Popularity
  addRow("Popularity", `⭐ ${r.stars || 0} | 🍴 ${r.forks || 0}`);

  return table;
}

function toggleDetails(safeId) {
  const details = document.getElementById("details-" + safeId);
  const chevron = document.getElementById("chevron-" + safeId);
  if (details.style.display === "none" || details.style.display === "") {
    details.style.display = "block";
    chevron.classList.add("rotate");
  } else {
    details.style.display = "none";
    chevron.classList.remove("rotate");
  }
}

async function runScan(repo, button) {
  if (!repo || !button) return;

  const originalText = button.innerHTML;
  button.disabled = true;
  button.innerHTML = '<span class="spinner"></span>';

  try {
    const resp = await fetch("/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ repo })
    });

    const data = await resp.json();
    if (!resp.ok) {
      alert(`Failed to submit scan: ${data.error}`);
      button.disabled = false;
      button.innerHTML = originalText;
      return;
    }

    const jobId = data.job_id;

    const poll = setInterval(async () => {
      const statusResp = await fetch(`/scan_status/${jobId}`);
      const statusData = await statusResp.json();

      if (statusData.status === "done" || statusData.status === "error") {
        clearInterval(poll);
        button.innerHTML = '✔';
        button.disabled = false;

        button.onclick = () => {
          button.innerHTML = originalText;
          button.onclick = e => { e.stopPropagation(); runScan(repo, button); };
        };
      }
    }, 2000);

  } catch (err) {
    console.error(err);
    alert(`Error submitting scan: ${err}`);
    button.disabled = false;
    button.innerHTML = originalText;
  }
}


window.onload = loadReports;
