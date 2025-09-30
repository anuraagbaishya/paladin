import React, { useEffect, useState } from "react";
import GhsaReportGroup from "./components/GhsaReportGroup";
import Header from "./components/Header";
import FilterPanel from "./components/FilterPanel";
import filterIcon from "./assets/filter.png";
import "./styles.css";

export default function IndexPage() {
    const [groups, setGroups] = useState([]);
    const [error, setError] = useState(null);
    const [query, setQuery] = useState("");
    const [showAlert, setShowAlert] = useState(false);
    const [days, setDays] = useState(7);
    const [editingDays, setEditingDays] = useState(false);
    const [repoFilter, setRepoFilter] = useState("all");
    const [ecosystemFilter, setEcosystemFilter] = useState("all");
    const [severityFilter, setSeverityFilter] = useState("all");
    const [showFilters, setShowFilters] = useState(false);

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
        .map(group => {
            const filteredFindings = group.findings.filter(report => {
                const haystack = [
                    report.title, report.cve, report.ghsa, report.cwe?.title,
                    report.severity, report.package, report.ecosystem,
                    group.repo, group.pkg
                ].filter(Boolean).join(" ").toLowerCase();

                if (!haystack.includes(query.toLowerCase())) return false;
                if (repoFilter === "withRepo" && !group.repo) return false;
                if (repoFilter === "withoutRepo" && group.repo) return false;
                if (ecosystemFilter !== "all" && report.ecosystem !== ecosystemFilter) return false;
                if (severityFilter !== "all" && report.severity?.toLowerCase() !== severityFilter) return false;

                return true;
            });
            return { ...group, findings: filteredFindings };
        })
        .filter(group => group.findings.length > 0);

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
            <Header
                days={days} setDays={setDays}
                editingDays={editingDays} setEditingDays={setEditingDays}
                handleRefresh={handleRefresh}
            >
                {/* Small components stay here */}
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

                <button className="filters-button" onClick={() => setShowFilters(true)}>
                    <img src={filterIcon} className="filters-icon" />
                    Filters
                </button>
            </Header>

            {showAlert && <div className="refresh-alert">Refreshing...</div>}

            <FilterPanel
                showFilters={showFilters} setShowFilters={setShowFilters}
                repoFilter={repoFilter} setRepoFilter={setRepoFilter}
                ecosystemFilter={ecosystemFilter} setEcosystemFilter={setEcosystemFilter}
                severityFilter={severityFilter} setSeverityFilter={setSeverityFilter}
            />

            <div id="reports">
                {filteredGroups.length > 0 ? filteredGroups.map((group, idx) => (
                    <GhsaReportGroup key={idx} group={group} />
                )) : <p>No findings match your search.</p>}
            </div>
        </div>
    );
}
