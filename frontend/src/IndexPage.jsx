import React, { useEffect, useState } from "react";
import ReportGroup from "./components/ReportGroup";
import "./styles.css";

export default function IndexPage() {
    const [groups, setGroups] = useState([]);
    const [error, setError] = useState(null);
    const [query, setQuery] = useState("");
    const [showAlert, setShowAlert] = useState(false);
    const [days, setDays] = useState(7);
    const [editingDays, setEditingDays] = useState(false);
    const [daysInput, setDaysInput] = useState("7");

    useEffect(() => {
        async function loadReports() {
            try {
                const resp = await fetch("/api/vuln_reports");
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

    const filteredGroups = groups
        .map((group) => {
            const filteredFindings = group.findings.filter((report) => {
                const haystack = [
                    report.title,
                    report.cve,
                    report.ghsa,
                    report.cwe?.title,
                    report.severity,
                    report.package,
                    group.repo,
                    group.pkg,
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                return haystack.includes(query.toLowerCase());
            });
            return { ...group, findings: filteredFindings };
        })
        .filter((group) => group.findings.length > 0);

    const handleRefresh = async (refreshDays = days) => {
        try {
            setShowAlert(true);
            await fetch(`/api/refresh_reports?days=${refreshDays}`);
            setTimeout(() => setShowAlert(false), 2000);
        } catch (err) {
            console.error("Failed to refresh reports", err);
            setShowAlert(false);
        }
    };

    return (
        <div className="app-container">
            {/* Top Banner */}
            <header className="app-banner">
                <div className="banner-content">
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

                <div className="right-bar">
                    <div className="refresh-control">
                        <button className="refresh-main" onClick={() => handleRefresh(days)}>
                            Refresh
                        </button>

                        <div className="refresh-days-container">
                            {editingDays ? (
                                <input
                                    type="text"
                                    className="days-input-inline"
                                    value={days}
                                    onChange={(e) => setDays(e.target.value)} // e.target.value is a string
                                    onBlur={() => setEditingDays(false)}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" || e.key === "Escape") e.target.blur();
                                    }}
                                    autoFocus
                                />
                            ) : (
                                <span className="days-display" onClick={() => setEditingDays(true)}>
                                    {days} days
                                </span>
                            )}

                            <span
                                className="refresh-chevron"
                                onMouseDown={(e) => e.preventDefault()} // keep focus on input
                                onClick={() => setEditingDays((prev) => !prev)}
                            >
                                ▼
                            </span>
                        </div>
                    </div>

                    <div className="search-wrapper">
                        <svg
                            className="search-icon"
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            width="16"
                            height="16"
                        >
                            <path d="M10 2a8 8 0 105.293 14.707l4.387 4.386 1.414-1.414-4.386-4.387A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z" />
                        </svg>
                        <input
                            type="text"
                            placeholder="Search across all repos..."
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            className="search-input"
                        />
                    </div>
                </div>
            </header>

            {showAlert && <div className="refresh-alert">Refreshing...</div>}

            {/* Reports List */}
            <div id="reports">
                {filteredGroups.length > 0 ? (
                    filteredGroups.map((group, idx) => (
                        <ReportGroup key={idx} group={group} />
                    ))
                ) : (
                    <p>No findings match your search.</p>
                )}
            </div>
        </div>
    );
}
