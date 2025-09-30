import React, { useEffect, useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function FileViewer({ filePath, startLine, endLine }) {
    const [lines, setLines] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchFile() {
            try {
                const resp = await fetch("/api/file", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ file_path: filePath }),
                });

                const data = await resp.json();
                if (!resp.ok) throw new Error(data.error || "Failed to fetch file");

                setLines(data.file || []);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        fetchFile();
    }, [filePath]);

    if (loading) return <div>Loading file...</div>;
    if (error) return <div style={{ color: "red" }}>{error}</div>;

    const language = detectLanguage(filePath);

    return (
        <SyntaxHighlighter
            language={language}
            style={dracula}
            showLineNumbers
            wrapLines={true}  // required to style individual lines
            lineProps={(lineNumber) => {
                if (lineNumber >= startLine && lineNumber <= endLine) {
                    return { style: { backgroundColor: "rgba(240, 34, 6, 0.89)" } };
                }
                return {};
            }}
            customStyle={{ background: "#010d1f", padding: "8px 0", fontSize: "0.9em" }}
        >
            {lines.join("")}
        </SyntaxHighlighter>
    );
}

function detectLanguage(filePath) {
    if (!filePath) return "text"; // fallback

    const ext = filePath.split(".").pop().toLowerCase();

    const mapping = {
        js: "javascript",
        jsx: "jsx",
        ts: "typescript",
        tsx: "tsx",
        py: "python",
        go: "go",
        java: "java",
        rb: "ruby",
        php: "php",
        cs: "csharp",
        cpp: "cpp",
        h: "cpp",
        html: "html",
        css: "css",
        scss: "scss",
        json: "json",
        yaml: "yaml",
        yml: "yaml",
        sh: "bash",
        bash: "bash",
        zsh: "bash",
        xml: "xml",
        txt: "text",
    };

    return mapping[ext] || "text"; // fallback to plain text
}
