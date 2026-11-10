import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { TeamDashboard } from "./pages/TeamDashboard";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/teams/:id" element={<TeamDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
