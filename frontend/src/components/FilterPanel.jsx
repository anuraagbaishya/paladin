import React from "react";

export default function FilterPanel({
    showFilters, setShowFilters,
    repoFilter, setRepoFilter,
    ecosystemFilter, setEcosystemFilter,
    severityFilter, setSeverityFilter
}) {
    return (
        <>
            {showFilters && <div className="filter-backdrop" onClick={() => setShowFilters(false)} />}
            <div className={`filter-panel ${showFilters ? "open" : ""}`}>
                <div className="filter-header">
                    <h3>Filters</h3>
                    <button className="close-button" onClick={() => setShowFilters(false)}>✕</button>
                </div>

                <div className="filter-section">
                    <label>Repo:</label>
                    <label>
                        <input type="radio" value="all" checked={repoFilter === "all"} onChange={() => setRepoFilter("all")} /> All
                    </label>
                    <label>
                        <input type="radio" value="withRepo" checked={repoFilter === "withRepo"} onChange={() => setRepoFilter("withRepo")} /> With Repo
                    </label>
                    <label>
                        <input type="radio" value="withoutRepo" checked={repoFilter === "withoutRepo"} onChange={() => setRepoFilter("withoutRepo")} /> Without Repo
                    </label>
                </div>

                <div className="filter-section">
                    <label>Ecosystem:</label>
                    <select value={ecosystemFilter} onChange={e => setEcosystemFilter(e.target.value)}>
                        <option value="all">All</option>
                        <option value="pip">Pip</option>
                        <option value="npm">NPM</option>
                        <option value="maven">Maven</option>
                        <option value="go">Go</option>
                        <option value="other">Other</option>
                    </select>
                </div>

                <div className="filter-section">
                    <label>Severity:</label>
                    <select value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
                        <option value="all">All</option>
                        <option value="critical">Critical</option>
                        <option value="high">High</option>
                        <option value="medium">Medium</option>
                        <option value="low">Low</option>
                    </select>
                </div>
            </div>
        </>
    );
}
