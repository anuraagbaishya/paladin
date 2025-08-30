import React, { useEffect, useState } from "react";
import ReportGroup from "./components/ReportGroup";
import "./styles.css";

export default function App() {
  const [groups, setGroups] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function loadReports() {
      try {
        const resp = await fetch("/vuln_reports");
        const data = await resp.json();
        setGroups(data);
      } catch (err) {
        console.error("Error loading reports:", err);
        setError("Failed to load reports.");
      }
    }

    loadReports();
  }, []);

  if (error) return <div>{error}</div>;

  return (
    <div>
      <h1>Semgrep Vulnerability Scanner</h1>
      <div id="reports">
        {groups.map((group, idx) => (
          <ReportGroup key={idx} group={group} />
        ))}
      </div>
    </div>
  );
}
