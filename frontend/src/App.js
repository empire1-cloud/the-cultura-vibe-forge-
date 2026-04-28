import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Signup from "./pages/Signup";
import Dashboard from "./pages/Dashboard";
import Taller from "./pages/Taller";
import ArtifactView from "./pages/ArtifactView";
import Billing from "./pages/Billing";
import Drafts from "./pages/Drafts";
import "./App.css";

function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="p-16 text-slate-500 text-sm">Loading...</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function Shell() {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-16 text-slate-500 text-sm">Loading...</div>;
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Layout>
            {user ? <Navigate to="/dashboard" replace /> : <Landing />}
          </Layout>
        }
      />
      <Route
        path="/login"
        element={
          <Layout>
            {user ? <Navigate to="/dashboard" replace /> : <Login />}
          </Layout>
        }
      />
      <Route
        path="/signup"
        element={
          <Layout>
            {user ? <Navigate to="/dashboard" replace /> : <Signup />}
          </Layout>
        }
      />
      <Route
        path="/dashboard"
        element={
          <RequireAuth>
            <Layout>
              <Dashboard />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/taller"
        element={
          <RequireAuth>
            <Layout>
              <Taller />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/artifact/:id"
        element={
          <RequireAuth>
            <Layout>
              <ArtifactView />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/billing"
        element={
          <RequireAuth>
            <Layout>
              <Billing />
            </Layout>
          </RequireAuth>
        }
      />
      <Route
        path="/drafts"
        element={
          <RequireAuth>
            <Layout>
              <Drafts />
            </Layout>
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <Shell />
          <Toaster
            theme="dark"
            position="bottom-right"
            toastOptions={{
              style: {
                background: "#121212",
                border: "1px solid rgba(255,255,255,0.1)",
                color: "#fff",
                borderRadius: "4px",
              },
            }}
          />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
