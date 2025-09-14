import React from "react";

export default function SearchBar({ query, setQuery }) {
    return (
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
    );
}
