import { useState } from "react";
import SarifReport from "./SarifReport";

export default function SarifReportGroup({ findings }) {
    const [expandedGroups, setExpandedGroups] = useState({});
    const [currentFindings, setCurrentFindings] = useState(findings ?? []);

    // Group findings by ruleId
    const grouped = currentFindings.reduce((acc, f) => {
        const rule = f.ruleId || "unknown";
        if (!acc[rule]) acc[rule] = [];
        acc[rule].push(f);
        return acc;
    }, {});

    const toggleGroup = (ruleId) => {
        setExpandedGroups(prev => ({ ...prev, [ruleId]: !prev[ruleId] }));
    };

    const handleRemoveFinding = (findingToRemove) => {
        setCurrentFindings(prev =>
            prev.filter(f => f !== findingToRemove)
        );
    };

    return (
        <div className="sarif-report">
            {Object.entries(grouped).map(([ruleId, ruleFindings]) => {
                const isExpanded = expandedGroups[ruleId];
                if (ruleFindings.length === 0) return null; // hide empty groups
                return (
                    <div key={ruleId} className="report-group">
                        <div className="report-group-header" onClick={() => toggleGroup(ruleId)}>
                            <div className="header-left">
                                <span className={`report-chevron ${isExpanded ? "rotate" : ""}`}>
                                    ▶
                                </span>
                                <h3>{ruleId} : {ruleFindings.length} finding(s)</h3>
                            </div>
                        </div>

                        {isExpanded && (
                            <div className="group-findings">
                                {ruleFindings.map((f, idx) => (
                                    <SarifReport
                                        key={`${ruleId}_${idx}`}
                                        finding={f}
                                        onRemove={handleRemoveFinding}
                                    />
                                ))}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
