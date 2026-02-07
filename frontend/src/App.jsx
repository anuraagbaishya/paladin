import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import NavHeader from "./components/NavHeader";
import HomePage from "./HomePage";
import ScansPage from "./ScansPage";
import AdvisoriesPage from "./AdvisoriesPage";
import SarifPage from "./SarifPage";

export default function App() {
  return (
    <Router>
      <NavHeader />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/scans" element={<ScansPage />} />
        <Route path="/advisories" element={<AdvisoriesPage />} />
        <Route path="/scan/:owner/:repo/:id" element={<SarifPage />} />
      </Routes>
    </Router>
  );
}
