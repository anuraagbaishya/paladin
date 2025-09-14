import React from "react";
import RefreshControl from "./RefreshControl";

export default function Header({
    days, setDays, editingDays, setEditingDays, handleRefresh,
    children // for search bar & filter button
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
                <RefreshControl
                    days={days}
                    setDays={setDays}
                    editingDays={editingDays}
                    setEditingDays={setEditingDays}
                    handleRefresh={handleRefresh}
                />
                {children}
            </div>
        </header>
    );
}
