import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./index.css";
import UploadPage from "./pages/UploadPage";
import DashboardPage from "./pages/DashboardPage";
import ResultsPage from "./pages/ResultsPage";
import AppLayout from "./components/AppLayout";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppLayout>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/jobs/:jobId" element={<DashboardPage />} />
          <Route path="/jobs/:jobId/results" element={<ResultsPage />} />
        </Routes>
      </AppLayout>
    </BrowserRouter>
  </React.StrictMode>
);
