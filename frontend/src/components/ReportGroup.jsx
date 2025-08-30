import { useState } from "react";
import Report from "./Report.jsx";

export default function ReportGroup({ group }) {
    const [scanMessages, setScanMessages] = useState({});
    const [scanningRepos, setScanningRepos] = useState({});

    const runScan = async (repo) => {
        if (!repo) return;

        // Set spinner and temporary message
        setScanningRepos((prev) => ({ ...prev, [repo]: true }));
        setScanMessages((prev) => ({ ...prev, [repo]: "Scanning..." }));

        try {
            const resp = await fetch("/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo }),
            });
            const data = await resp.json();
            if (!resp.ok) {
                setScanningRepos((prev) => ({ ...prev, [repo]: false }));
                setScanMessages((prev) => ({ ...prev, [repo]: `Error: ${data.error}` }));
                setTimeout(() => {
                    setScanMessages((prev) => ({ ...prev, [repo]: "" }));
                }, 10000);
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
                    setTimeout(() => {
                        setScanMessages((prev) => ({ ...prev, [repo]: "" }));
                    }, 10000);
                }
            }, 2000);
        } catch (err) {
            console.error(err);
            setScanningRepos((prev) => ({ ...prev, [repo]: false }));
            setScanMessages((prev) => ({ ...prev, [repo]: `Error: ${err}` }));
            setTimeout(() => {
                setScanMessages((prev) => ({ ...prev, [repo]: "" }));
            }, 10000);
        }
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
                    <button
                        className="scan-btn"
                        disabled={!group.repo || scanningRepos[group.repo]}
                        onClick={e => {
                            e.stopPropagation();
                            runScan(group.repo);
                        }}
                    >
                        {scanningRepos[group.repo] ? <span className="spinner"></span> : "Scan"}
                    </button>
                </div>

            </div>

            <div className="group-findings">
                {group.findings.map((report, idx) => {
                    const safeId = `${group.repo || group.pkg || "unknown"}_${idx}`;
                    return <Report key={safeId} report={report} id={safeId} />;
                })}
            </div>
        </div>
    );
}
