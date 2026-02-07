import React from "react";
import { NavLink } from "react-router-dom";

export default function NavHeader() {
    return (
        <header className="nav-header">
            <div className="nav-left">
                <NavLink to="/" className="logo-link">
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
                </NavLink>
            </div>
            <nav className="nav-links">
                <NavLink to="/" end className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
                    Home
                </NavLink>
                <NavLink to="/scans" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
                    Scans
                </NavLink>
                <NavLink to="/advisories" className={({ isActive }) => isActive ? "nav-link active" : "nav-link"}>
                    GH Advisories
                </NavLink>
            </nav>
        </header>
    );
}
