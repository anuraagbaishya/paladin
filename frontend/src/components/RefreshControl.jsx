import React from "react";

export default function RefreshControl({ days, setDays, editingDays, setEditingDays, handleRefresh }) {
    return (
        <div className="refresh-control">
            <button className="refresh-main" onClick={() => handleRefresh(days)}>
                Refresh
            </button>

            <div className="refresh-days-container">
                {editingDays ? (
                    <input
                        type="text"
                        className="days-input-inline"
                        value={days}
                        onChange={(e) => setDays(e.target.value)}
                        onBlur={() => setEditingDays(false)}
                        onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === "Escape") e.target.blur();
                        }}
                        autoFocus
                    />
                ) : (
                    <span className="days-display" onClick={() => setEditingDays(true)}>
                        {days} days
                    </span>
                )}

                <span
                    className="refresh-chevron"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => setEditingDays((prev) => !prev)}
                >
                    ▼
                </span>
            </div>
        </div>
    );
}
