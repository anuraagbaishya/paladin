import { useState } from "react";
import FileViewer from "./FileViewer";
import { useParams } from "react-router-dom";

function SarifReport({ finding, onRemove }) {
    const [showFile, setShowFile] = useState(false);
    const [suppressed, setSuppressed] = useState(false);
    const { id: scanId } = useParams(); // gets scan id from URL

    const loc = finding.locations?.[0]?.physicalLocation;
    const startLine = loc?.region?.startLine;
    const endLine = loc?.region?.endLine;
    const snippet = loc?.region?.snippet?.text;
    const file = loc?.artifactLocation?.uri;

    if (suppressed) return null; // hide suppressed findings

    const handleSuppress = async () => {
        if (!finding.fingerprints) return;

        try {
            const fingerprintId = Object.values(finding.fingerprints)[0]; // get the fingerprint
            const resp = await fetch(`/api/sarif/${scanId}/suppress?fingerprint=${fingerprintId}`, {
                method: "GET",
            });

            if (!resp.ok) throw new Error("Failed to suppress finding");
            setSuppressed(true); // hide this finding in UI
            if (onRemove) onRemove(finding);
        } catch (err) {
            console.error("Error suppressing finding:", err);
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
                </div>

                {showFile && file && <FileViewer filePath={file} />}
            </div>
        </div>
    );
}

export default SarifReport;
