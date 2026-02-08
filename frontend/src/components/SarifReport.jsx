import { useState } from "react";
import FileViewer from "./FileViewer";
import { useParams } from "react-router-dom";

function SarifReport({ finding, onRemove }) {
    const [showFile, setShowFile] = useState(false);
    const [aiReview, setAiReview] = useState(finding.aiReview || null); // show existing review by default
    const [loadingAiReview, setLoadingAiReview] = useState(false);
    const [localSuppressed, setLocalSuppressed] = useState(finding.suppressed || false);
    const { id: scanId } = useParams();

    const { file, startLine, endLine, snippet, description, fingerprint } = finding;

    if (localSuppressed) return null;

    const handleSuppress = async () => {
        if (!fingerprint) return;

        setLocalSuppressed(true);
        if (onRemove) onRemove(finding);

        try {
            const resp = await fetch(`/api/sarif/${scanId}/suppress?fingerprint=${fingerprint}`, {
                method: "GET",
            });

            if (!resp.ok) throw new Error("Failed to suppress finding");
        } catch (err) {
            console.error("Error suppressing finding:", err);
            setLocalSuppressed(false);
        }
    };

    const handleAiReview = async () => {
        if (!fingerprint) return;

        setLoadingAiReview(true);
        try {
            const resp = await fetch(`/api/scan/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scan_id: scanId,
                    fingerprint_id: fingerprint,
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
                {startLine && (
                    <p>
                        <strong>Lines:</strong> {startLine}
                        {endLine && startLine !== endLine ? `-${endLine}` : ""}
                    </p>
                )}
                {snippet && <pre>{snippet}</pre>}
                {description && <p>{description}</p>}

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

                {aiReview && aiReview.reason && (
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
