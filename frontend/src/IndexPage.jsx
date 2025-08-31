import React, { useEffect, useState } from "react";
import ReportGroup from "./components/ReportGroup";
import "./styles.css";

export default function IndexPage() {
    const [groups, setGroups] = useState([]);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadReports() {
            try {
                const resp = await fetch("/api/vuln_reports"); // <-- backend path
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
        <div className="app-container">
            {/* Top Banner */}
            <header className="app-banner">
                <div className="banner-content">
                    {/* Shield icon */}
                    <svg
                        className="shield-icon"
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        width="32"
                        height="32"
                    >
                        <path d="M12 2L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-3z" />
                    </svg>
                    <h1>PALADIN</h1>
                </div>
            </header>

            {/* Reports List */}
            <div id="reports">
                {groups.map((group, idx) => (
                    <ReportGroup key={idx} group={group} />
                ))}
            </div>
        </div>
    );


}
