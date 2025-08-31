import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import IndexPage from "./IndexPage";
import SarifPage from "./SarifPage";

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<IndexPage />} />
        <Route path="/sarif/:id" element={<SarifPage />} />
      </Routes>
    </Router>
  );
}
