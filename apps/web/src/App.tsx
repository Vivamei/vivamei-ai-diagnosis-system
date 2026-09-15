import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import { ProtectedRoute } from "@/components/ProtectedRoute";

const Home = lazy(() => import("@/pages/Home"));
const Login = lazy(() => import("@/pages/Login"));
const Entry = lazy(() => import("@/pages/Entry"));
const Capture = lazy(() => import("@/pages/Capture"));
const Analyzing = lazy(() => import("@/pages/Analyzing"));
const Report = lazy(() => import("@/pages/Report"));
const RadarDetail = lazy(() => import("@/pages/RadarDetail"));
const Booking = lazy(() => import("@/pages/Booking"));
const LegalPage = lazy(() => import("@/pages/LegalPage"));

export default function App() {
  return (
    <Suspense fallback={<div className="loading">加载中…</div>}>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<Login />} />
        <Route path="/entry" element={<Entry />} />
        <Route path="/legal/:kind" element={<LegalPage />} />

        {/* 需登录 */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Home />
            </ProtectedRoute>
          }
        />
        <Route
          path="/capture"
          element={
            <ProtectedRoute>
              <Capture />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analyzing/:id"
          element={
            <ProtectedRoute>
              <Analyzing />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report/:id"
          element={
            <ProtectedRoute>
              <Report />
            </ProtectedRoute>
          }
        />
        <Route
          path="/report/:id/:axis"
          element={
            <ProtectedRoute>
              <RadarDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/booking"
          element={
            <ProtectedRoute>
              <Booking />
            </ProtectedRoute>
          }
        />
      </Routes>
    </Suspense>
  );
}
