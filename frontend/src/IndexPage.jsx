import React, { useEffect, useState } from "react";
import GhsaReportGroup from "./components/GhsaReportGroup";
import Header from "./components/Header";
import FilterPanel from "./components/FilterPanel";
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

    const pollJobStatus = (jobId, interval = 5000) => {
        return new Promise((resolve, reject) => {
            const poll = setInterval(async () => {
                try {
                    const res = await fetch(`/api/job_status/${jobId}`);
                    const data = await res.json();

                    if (!res.ok) {
                        clearInterval(poll);
                        return reject(data.error || "Failed to get job status");
                    }

                    if (data.status === "done") {
                        clearInterval(poll);
                        resolve(data);
                    } else if (data.status === "error") {
                        clearInterval(poll);
                        reject(data);
                    }
                } catch (err) {
                    clearInterval(poll);
                    reject(err);
                }
            }, interval);
        });
    };

    const handleRefresh = async (refreshDays = days) => {
        try {
            setShowAlert("pending");

            const resp = await fetch(`/api/refresh_reports?days=${refreshDays}`);
            const data = await resp.json();

            if (!resp.ok) {
                console.error("Refresh failed:", data.error || data);
                setShowAlert(false);
                return;
            }

            const jobId = data._id;
            console.log("Refresh job started:", jobId);

            try {
                await pollJobStatus(jobId);
                console.log("Refresh complete");

                await loadReports();

                setShowAlert("done");
                setTimeout(() => setShowAlert(false), 3000);
            } catch (err) {
                console.error("Refresh errored:", err);
                setShowAlert("error");
                setTimeout(() => setShowAlert(false), 3000);
            }

        } catch (err) {
            console.error("Failed to refresh reports", err);
            setShowAlert(false);
        }
    };


    const loadReports = async () => {
        try {
            const resp = await fetch("/api/reports");
            const data = await resp.json();
            setGroups(data);
        } catch (err) {
            console.error("Error loading reports:", err);
            setError("Failed to load reports.");
        }
    };

    useEffect(() => {
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

    return (
        <div className="app-container">
            <Header
                days={days} setDays={setDays}
                editingDays={editingDays} setEditingDays={setEditingDays}
                handleRefresh={handleRefresh}
                query={query} setQuery={setQuery}
                setShowFilters={setShowFilters}
            />

            {showAlert && (
                <div className="refresh-alert">
                    {showAlert === "pending" && "Refreshing..."}
                    {showAlert === "done" && "Refresh complete!"}
                    {showAlert === "error" && "Refresh failed!"}
                </div>
            )}


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
