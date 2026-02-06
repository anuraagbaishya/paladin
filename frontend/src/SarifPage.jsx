import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import SarifReportGroup from "./components/SarifReportGroup";
import { Link } from "react-router-dom";

export default function SarifPage() {
    const { owner, repo, id } = useParams();
    const [scanData, setScanData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadScan() {
            try {
                const resp = await fetch(`/api/scan/${owner}/${repo}/${id}`);
                if (!resp.ok) throw new Error("Failed to fetch scan");
                const data = await resp.json();
                setScanData(data);
            } catch (err) {
                console.error("Error loading scan:", err);
                setError("Failed to load scan report.");
            }
        }
        loadScan();
    }, [owner, repo, id]);

    if (error) return <div>{error}</div>;
    if (!scanData) return <div>Loading scan report...</div>;

    const findings = scanData.results ?? [];

    return (
        <div className="app-container">
            <header className="app-banner">
                <div className="banner-content">
                    <Link to="/" className="logo-link">
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
                    </Link>
                </div>
            </header>

            <main className="p-4">
                <SarifReportGroup findings={findings} groupName="SARIF Findings" />
            </main>
        </div>
    );
}
