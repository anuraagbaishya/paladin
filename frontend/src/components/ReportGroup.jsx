import { useState } from "react";
import Report from "./Report.jsx";

export default function ReportGroup({ group }) {
    const [scanMessages, setScanMessages] = useState({});
    const [scanningRepos, setScanningRepos] = useState({});
    const [scans, setScans] = useState([]);
    const [showScans, setShowScans] = useState(false);

    const runScan = async (repo) => {
        if (!repo) return;

        setScanningRepos((prev) => ({ ...prev, [repo]: true }));
        setScanMessages((prev) => ({ ...prev, [repo]: "Scanning..." }));

        try {
            const resp = await fetch("/api/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                setScanningRepos((prev) => ({ ...prev, [repo]: false }));
                setScanMessages((prev) => ({ ...prev, [repo]: `Error: ${data.error}` }));
                setTimeout(() => setScanMessages((prev) => ({ ...prev, [repo]: "" })), 10000);
                return;
            }

            const jobId = data.job_id;

            const poll = setInterval(async () => {
                const statusResp = await fetch(`/scan_status/${jobId}`);
                const statusData = await statusResp.json();
                if (statusData.status === "done" || statusData.status === "error") {
                    clearInterval(poll);
                    setScanningRepos((prev) => ({ ...prev, [repo]: false }));
                    setScanMessages((prev) => ({ ...prev, [repo]: "Scan complete" }));
                    setTimeout(() => setScanMessages((prev) => ({ ...prev, [repo]: "" })), 10000);
                }
            }, 5000);
        } catch (err) {
            console.error(err);
            setScanningRepos((prev) => ({ ...prev, [repo]: false }));
            setScanMessages((prev) => ({ ...prev, [repo]: `Error: ${err}` }));
            setTimeout(() => setScanMessages((prev) => ({ ...prev, [repo]: "" })), 10000);
        }
    };

    const handleToggleScans = async (repo) => {
        if (showScans) {
            setShowScans(false);
        } else {
            try {
                const response = await fetch(`/api/scans/${encodeURIComponent(repo)}`);
                if (!response.ok) throw new Error("Network response was not ok");
                const data = await response.json();
                setScans(data);
                setShowScans(true);
            } catch (error) {
                console.error("Fetch error:", error);
            }
        }
    };

    const formatTimestamp = (ts) => {
        const d = new Date(ts * 1000);
        return d.toLocaleString(); // e.g., "2025-01-01, 12:00:00 PM"
    };

    return (
        <div className="report-group">
            <div className="report-group-header">
                <h3>
                    {group.repo ? group.repo.split("/").pop() : group.pkg || "Unknown"}: {group.findings.length} finding(s)
                </h3>
                <div className="scan-container">
                    {scanMessages[group.repo] && (
                        <span className="scan-message">{scanMessages[group.repo]}</span>
                    )}
                    {group.repo && (
                        <>
                            <button
                                className="scan-btn"
                                disabled={scanningRepos[group.repo]}
                                onClick={e => {
                                    e.stopPropagation();
                                    runScan(group.repo);
                                }}
                            >
                                {scanningRepos[group.repo] ? <span className="spinner"></span> : "Scan"}
                            </button>

                            <button
                                className="get-scans-btn"
                                disabled={scanningRepos[group.repo]}
                                onClick={() => handleToggleScans(group.repo)}
                            >
                                {showScans ? "Hide Scans" : "Show Scans"}
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div className="group-findings">
                {group.findings.map((report, idx) => {
                    const safeId = `${group.repo || group.pkg || "unknown"}_${idx}`;
                    return <Report key={safeId} report={report} id={safeId} />;
                })}
            </div>

            {/* Area to display fetched scans */}
            {showScans && (
                <div className="scan-results">
                    <h4>Scan Results:</h4>
                    {scans.length > 0 ? (
                        <ul>
                            {scans.map((scan) => (
                                <li key={scan._id}>
                                    <p><a href={`/sarif/${scan._id}`} target="_blank" rel="noopener noreferrer">
                                        Scanned at {formatTimestamp(scan.timestamp)}
                                    </a> {`${scan.findings_count}`} findings</p>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p>No results found</p>
                    )}
                </div>
            )}

        </div>
    );
}
