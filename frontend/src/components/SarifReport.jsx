import { useState } from "react";
import FileViewer from "./FileViewer";
import { useParams } from "react-router-dom";

function SarifReport({ finding, onRemove }) {
    const [showFile, setShowFile] = useState(false);
    const [aiReview, setAiReview] = useState(finding.aiReview || null); // show existing review by default
    const [loadingAiReview, setLoadingAiReview] = useState(false);
    const [localSuppressed, setLocalSuppressed] = useState(finding.suppressed || false);
    const { id: scanId } = useParams();

    const loc = finding.locations?.[0]?.physicalLocation;
    const startLine = loc?.region?.startLine;
    const endLine = loc?.region?.endLine;
    const snippet = loc?.region?.snippet?.text;
    const file = loc?.artifactLocation?.uri;

    if (localSuppressed) return null;

    const handleSuppress = async () => {
        if (!finding.fingerprints) return;

        setLocalSuppressed(true);
        if (onRemove) onRemove(finding);

        try {
            const fingerprintId = Object.values(finding.fingerprints)[0];
            const resp = await fetch(`/api/sarif/${scanId}/suppress?fingerprint=${fingerprintId}`, {
                method: "GET",
            });

            if (!resp.ok) throw new Error("Failed to suppress finding");
        } catch (err) {
            console.error("Error suppressing finding:", err);
            setLocalSuppressed(false);
        }
    };

    const handleAiReview = async () => {
        if (!finding.fingerprints) return;

        setLoadingAiReview(true);
        try {
            const fingerprintId = Object.values(finding.fingerprints)[0];
            const resp = await fetch(`/api/scan/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scan_id: scanId,
                    fingerprint_id: fingerprintId,
                }),
            });

            if (!resp.ok) throw new Error("Failed to get AI review");

            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            setAiReview(data.review); // update review even if it existed before
        } catch (err) {
            console.error("Error fetching AI review:", err);
        } finally {
            setLoadingAiReview(false);
        }
    };

    return (
        <div className="report finding-item">
            <div className="report-details">
                {file && <p><strong>File:</strong> {file}</p>}
                {loc && startLine && (
                    <p>
                        <strong>Lines:</strong> {startLine}
                        {endLine && startLine !== endLine ? `-${endLine}` : ""}
                    </p>
                )}
                {snippet && <pre>{snippet}</pre>}
                {finding.message?.text && <p>{finding.message.text}</p>}

                <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                    {file && (
                        <button onClick={() => setShowFile(prev => !prev)}>
                            {showFile ? "Hide File" : "View File"}
                        </button>
                    )}
                    <button onClick={handleSuppress}>Suppress</button>
                    <button onClick={handleAiReview} disabled={loadingAiReview}>
                        {loadingAiReview ? "Loading..." : "AI Review"}
                    </button>
                </div>

                {aiReview && (
                    <div style={{ marginTop: "8px" }}>
                        <p><strong>AI Verdict:</strong> {aiReview.verdict ? "Issue" : "Not an issue"}</p>
                        <p><strong>Reason:</strong> {aiReview.reason}</p>
                        <p style={{ fontStyle: "italic", fontSize: "0.85em", marginTop: "4px" }}>
                            *Disclaimer: This AI review is for guidance only and may not be fully accurate.*
                        </p>
                    </div>
                )}

                {showFile && file && <FileViewer filePath={file} startLine={startLine} endLine={endLine} />}
            </div>
        </div>
    );
}

export default SarifReport;
