import React, { useState } from "react";

export default function Report({ report, idBase, index }) {
    const [expanded, setExpanded] = useState(false);
    const safeId = `${(idBase || "unknown").replace(/\//g, "_")}_${index}`;

    const toggleDetails = () => setExpanded((prev) => !prev);

    const titleSummary = report.title || report.cve || "No title";

    const buildDetails = () => {
        const rows = [];

        function addRow(key, value) {
            if (!value) return;
            rows.push(
                <tr key={key}>
                    <td className="highlight-key">{key}</td>
                    <td className="highlight-value">
                        {typeof value === "string" || typeof value === "number" ? (
                            value
                        ) : (
                            value
                        )}
                    </td>
                </tr>
            );
        }

        if (report.repo) {
            const link = (
                <a href={`https://github.com/${report.repo}`} target="_blank">
                    {report.repo}
                </a>
            );
            addRow("Repo", link);
        } else {
            addRow("Package", report.package);
        }

        if (report.cve) {
            const link = (
                <a
                    href={`https://cve.mitre.org/cgi-bin/cvename.cgi?name=${report.cve}`}
                    target="_blank"
                >
                    {report.cve}
                </a>
            );
            addRow("CVE", link);
        }

        if (report.ghsa) {
            const link = (
                <a href={`https://github.com/advisories/${report.ghsa}`} target="_blank">
                    {report.ghsa}
                </a>
            );
            addRow("GHSA", link);
        }

        if (report.cwe) {
            const link = (
                <a
                    href={`https://cwe.mitre.org/data/definitions/${report.cwe.id}.html`}
                    target="_blank"
                >
                    CWE-{report.cwe.id}: {report.cwe.title}
                </a>
            );
            addRow("CWE", link);
        }

        if (report.cvss_score) addRow("CVSS Score", report.cvss_score);
        if (report.cvss_vector) addRow("CVSS Vector", report.cvss_vector);
        if (report.severity) addRow("Severity", report.severity);
        if (report.stars || report.forks)
            addRow("Popularity", `⭐ ${report.stars || 0} | 🍴 ${report.forks || 0}`);

        return <table className="details-table">{rows}</table>;
    };

    return (
        <div className="report">
            <div className="report-header">
                <div className="header-left" onClick={toggleDetails}>
                    <span className={`chevron ${expanded ? "rotate" : ""}`} id={`chevron-${safeId}`}>
                        ▶
                    </span>
                    <p>{titleSummary}</p>
                </div>
            </div>
            {expanded && <div className="report-details">{buildDetails()}</div>}
        </div>
    );
}
