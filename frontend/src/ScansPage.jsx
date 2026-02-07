import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function ScansPage() {
    const [scans, setScans] = useState([]);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadScans() {
            try {
                const resp = await fetch("/api/scans");
                if (!resp.ok) throw new Error("Failed to fetch scans");
                const data = await resp.json();
                setScans(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        loadScans();
    }, []);

    const formatTimestamp = (ts) => {
        const d = new Date(ts * 1000);
        return d.toLocaleString();
    };

    const handleDelete = async (scanId) => {
        try {
            await fetch(`/api/scans/delete/${scanId}`, { method: "DELETE" });
            setScans(prev => prev.filter(s => s.scan_id !== scanId));
        } catch (err) {
            console.error("Failed to delete scan", err);
        }
    };

    // Group by repo
    const grouped = scans.reduce((acc, scan) => {
        const repo = scan.repo || "Unknown";
        if (!acc[repo]) acc[repo] = [];
        acc[repo].push(scan);
        return acc;
    }, {});

    // Filter by query
    const filteredRepos = Object.keys(grouped).filter(repo =>
        repo.toLowerCase().includes(query.toLowerCase())
    );

    if (loading) return (
        <div className="app-container">
            <div className="page-toolbar">
                <div className="search-wrapper">
                    <svg className="search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                        <path d="M10 2a8 8 0 105.293 14.707l4.387 4.386 1.414-1.414-4.386-4.387A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z" />
                    </svg>
                    <input type="text" placeholder="Search repos..." className="search-input" disabled />
                </div>
            </div>
            <p style={{ textAlign: "center", marginTop: "40px" }}>Loading scans...</p>
        </div>
    );

    if (error) return (
        <div className="app-container">
            <p style={{ textAlign: "center", marginTop: "40px" }}>{error}</p>
        </div>
    );

    return (
        <div className="app-container">
            <div className="page-toolbar">
                <div className="search-wrapper">
                    <svg className="search-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                        <path d="M10 2a8 8 0 105.293 14.707l4.387 4.386 1.414-1.414-4.386-4.387A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z" />
                    </svg>
                    <input
                        type="text"
                        placeholder="Search repos..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="search-input"
                    />
                </div>
            </div>

            <div className="scans-list">
                {filteredRepos.length > 0 ? filteredRepos.map(repo => (
                    <div key={repo} className="report" style={{ marginTop: "16px" }}>
                        <div className="report-group-header" style={{ marginLeft: 0 }}>
                            <h3>{repo}</h3>
                            <span style={{ color: "#888", fontSize: "0.9em" }}>
                                {grouped[repo].length} scan{grouped[repo].length !== 1 ? "s" : ""}
                            </span>
                        </div>
                        <div className="group-findings" style={{ marginLeft: 0 }}>
                            {grouped[repo].map(scan => (
                                <div key={scan.scan_id} className="scan-item">
                                    <Link to={`/scan/${repo}/${scan.scan_id}`}>
                                        {formatTimestamp(scan.timestamp)}
                                    </Link>
                                    {scan.languages && scan.languages.length > 0 && (
                                        <span className="scan-languages">
                                            {scan.languages.join(", ")}
                                        </span>
                                    )}
                                    <span style={{ color: "#888" }}>
                                        {scan.findings_count} finding{scan.findings_count !== 1 ? "s" : ""}
                                    </span>
                                    <button className="delete-btn" onClick={() => handleDelete(scan.scan_id)}>
                                        Delete
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                )) : (
                    <p className="no-results">No scans found.</p>
                )}
            </div>
        </div>
    );
}
