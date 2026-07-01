import { Routes, Route } from "react-router-dom";
import AnalysisPage from "./pages/AnalysisPage";
import HomePage from "./pages/HomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/analysis/:sessionId" element={<AnalysisPage />} />
    </Routes>
  );
}
