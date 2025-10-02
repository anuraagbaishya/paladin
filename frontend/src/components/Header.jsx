import React from "react";
import RefreshControl from "./RefreshControl";
import filterIcon from "../assets/filter.png"; // adjust path if needed

export default function Header({
    days, setDays, editingDays, setEditingDays, handleRefresh,
    query, setQuery, setShowFilters
}) {
    return (
        <header className="app-banner">
            <div className="banner-content">
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
            </div>

            <div className="right-bar">
                <div className="search-wrapper">
                    <svg
                        className="search-icon"
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                        width="16"
                        height="16"
                    >
                        <path d="M10 2a8 8 0 105.293 14.707l4.387 4.386 1.414-1.414-4.386-4.387A8 8 0 0010 2zm0 2a6 6 0 110 12 6 6 0 010-12z" />
                    </svg>
                    <input
                        type="text"
                        placeholder="Search across all repos..."
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        className="search-input"
                    />
                </div>

                <RefreshControl
                    days={days}
                    setDays={setDays}
                    editingDays={editingDays}
                    setEditingDays={setEditingDays}
                    handleRefresh={handleRefresh}
                />

                <button className="filters-button" onClick={() => setShowFilters(true)}>
                    <img src={filterIcon} className="filters-icon" />
                    Filters
                </button>
            </div>
        </header>
    );
}
