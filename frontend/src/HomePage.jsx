import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { pollJobStatus } from "./utils/jobPolling";

function parseGitHubRepo(input) {
    input = input.trim();
    // Handle full URLs: https://github.com/owner/repo
    try {
        const url = new URL(input);
        if (url.hostname === "github.com" || url.hostname === "www.github.com") {
            const parts = url.pathname.split("/").filter(Boolean);
            if (parts.length >= 2) {
                return `${parts[0]}/${parts[1]}`;
            }
        }
    } catch {
        // Not a URL, try as owner/repo
    }
    // Handle bare owner/repo format
    const match = input.match(/^([a-zA-Z0-9._-]+)\/([a-zA-Z0-9._-]+)$/);
    if (match) {
        return `${match[1]}/${match[2]}`;
    }
    return null;
}

export default function HomePage() {
    const [repoInput, setRepoInput] = useState("");
    const [scanning, setScanning] = useState(false);
    const [error, setError] = useState(null);
    const [scanStatus, setScanStatus] = useState(null);
    const [scanComplete, setScanComplete] = useState(null);
    const navigate = useNavigate();

    const handleScan = async () => {
        const repo = parseGitHubRepo(repoInput);
        if (!repo) {
            setError("Please enter a valid GitHub URL or owner/repo");
            return;
        }
        setError(null);
        setScanComplete(null);
        setScanning(true);
        setScanStatus("Starting scan...");

        const startTime = Math.floor(Date.now() / 1000);

        try {
            const resp = await fetch("/api/scan", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ repo }),
            });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.error || "Scan failed");

            const jobId = data._id;
            setScanStatus("Scanning repository...");

            await pollJobStatus(jobId);

            // Fetch the latest scan for this repo to get scan_id
            const scansResp = await fetch(`/api/scans/${encodeURIComponent(repo)}`);
            const scans = await scansResp.json();
            const latestScan = scans.length > 0 ? scans[0] : null;

            if (latestScan && latestScan.timestamp >= startTime && latestScan.findings_count > 0) {
                navigate(`/scan/${repo}/${latestScan.scan_id}`);
            } else {
                setScanComplete("Scan complete — no findings detected.");
            }
        } catch (err) {
            setError(err.message || "Scan failed");
        } finally {
            setScanning(false);
            setScanStatus(null);
        }
    };

    return (
        <div className="home-container">
            <div className="home-content">
                <h2 className="home-heading">What would you like to scan?</h2>
                <div className="home-input-group">
                    <input
                        type="text"
                        className="home-input"
                        placeholder="https://github.com/owner/repo"
                        value={repoInput}
                        onChange={(e) => { setRepoInput(e.target.value); setError(null); }}
                        onKeyDown={(e) => e.key === "Enter" && !scanning && repoInput.trim() && handleScan()}
                        disabled={scanning}
                    />
                    <button
                        className="home-scan-btn"
                        onClick={handleScan}
                        disabled={scanning || !repoInput.trim()}
                    >
                        {scanning ? <span className="spinner" /> : "Scan"}
                    </button>
                </div>
                {error && <p className="home-error">{error}</p>}
                {scanStatus && <p className="home-status">{scanStatus}</p>}
                {scanComplete && <p className="home-success">{scanComplete}</p>}

                <div className="home-links">
                    <Link to="/scans" className="home-link-card">Show Scans</Link>
                    <Link to="/advisories" className="home-link-card">See GitHub Advisories</Link>
                </div>
            </div>
        </div>
    );
}
