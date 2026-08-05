import { lazy, Suspense } from "react";
import { Redirect, Route, Switch, useLocation } from "wouter";

import AppLayout from "@/app/AppLayout";
import ErrorBoundary from "@/app/ErrorBoundary";
import { AppProviders } from "@/app/providers";
import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { env } from "@/config/env";
import Login from "@/pages/Login";
import NotFound from "@/pages/NotFound";

const Comparison = lazy(() => import("@/pages/Comparison"));
const CreateExperiment = lazy(() => import("@/pages/CreateExperiment"));
const Dashboard = lazy(() => import("@/pages/Dashboard"));
const OptimizationProgress = lazy(() => import("@/pages/OptimizationProgress"));
const Playground = lazy(() => import("@/pages/Playground"));
const Registry = lazy(() => import("@/pages/Registry"));
const ReviewApproval = lazy(() => import("@/pages/ReviewApproval"));
const Settings = lazy(() => import("@/pages/Settings"));

const legacyPagePaths = {
  dashboard: "/dashboard",
  experiments: "/projects/new",
  playground: "/playground",
  optimization: "/runs/demo",
  comparison: "/runs/demo/compare",
  review: "/review",
  registry: "/prompts",
  settings: "/settings",
} as const;

function LoginRoute() {
  const { user, signIn, error } = useAuth();
  const [, navigate] = useLocation();
  if (user) return <Redirect to="/dashboard" replace />;
  return (
    <Login
      onLogin={async () => {
        await signIn();
        navigate("/dashboard", { replace: true });
      }}
      connected={env.authMode === "firebase"}
      authError={error}
    />
  );
}

function DashboardRoute() {
  const [, navigate] = useLocation();
  return <Dashboard onNavigate={(page) => navigate(legacyPagePaths[page])} />;
}

function CreateExperimentRoute() {
  const [, navigate] = useLocation();
  return <CreateExperiment onNavigate={(page) => navigate(legacyPagePaths[page])} />;
}

function RouteLoading() {
  return (
    <div className="page-state" role="status">
      Loading page…
    </div>
  );
}

function RoutedApplication() {
  const { user, loading } = useAuth();
  const [location] = useLocation();
  if (loading) return <RouteLoading />;
  if (location === "/login") return <LoginRoute />;
  if (!user) return <Redirect to="/login" replace />;

  return (
    <AppLayout>
      <Suspense fallback={<RouteLoading />}>
        <Switch>
          <Route path="/">
            <Redirect to="/dashboard" replace />
          </Route>
          <Route path="/dashboard">
            <DashboardRoute />
          </Route>
          <Route path="/projects/new">
            <CreateExperimentRoute />
          </Route>
          <Route path="/playground">
            <Playground />
          </Route>
          <Route path="/runs/:runId/compare">
            <Comparison />
          </Route>
          <Route path="/runs/:runId">
            <OptimizationProgress />
          </Route>
          <Route path="/review">
            <ReviewApproval />
          </Route>
          <Route path="/prompts">
            <Registry />
          </Route>
          <Route path="/settings">
            <Settings />
          </Route>
          <Route>
            <NotFound />
          </Route>
        </Switch>
      </Suspense>
    </AppLayout>
  );
}

export function AppRouter() {
  return (
    <ErrorBoundary>
      <AppProviders>
        <AuthProvider>
          <RoutedApplication />
        </AuthProvider>
      </AppProviders>
    </ErrorBoundary>
  );
}
