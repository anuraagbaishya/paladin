import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import SarifReportGroup from "./components/SarifReportGroup";
import { Link } from "react-router-dom";

export default function SarifPage() {
    const { id } = useParams();
    const [sarifLog, setSarifLog] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function loadSarif() {
            try {
                const resp = await fetch(`/api/sarif/${id}`);
                if (!resp.ok) throw new Error("Failed to fetch SARIF");
                const data = await resp.json();
                setSarifLog(data);
            } catch (err) {
                console.error("Error loading SARIF:", err);
                setError("Failed to load SARIF report.");
            }
        }
        loadSarif();
    }, [id]);

    if (error) return <div>{error}</div>;
    if (!sarifLog) return <div>Loading SARIF report...</div>;

    // Extract all findings from all runs
    const findings = (sarifLog.runs ?? []).flatMap(run => run.results ?? []);

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
