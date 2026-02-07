import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import SarifReportGroup from "./components/SarifReportGroup";

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
            <main className="p-4">
                <SarifReportGroup findings={findings} groupName="SARIF Findings" />
            </main>
        </div>
    );
}
