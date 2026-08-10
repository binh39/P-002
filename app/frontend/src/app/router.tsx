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
const Datasets = lazy(() => import("@/pages/Datasets"));
const Experiments = lazy(() => import("@/pages/Experiments"));
const OptimizationRun = lazy(() => import("@/pages/OptimizationRun"));
const Playground = lazy(() => import("@/pages/Playground"));
const Registry = lazy(() => import("@/pages/Registry"));
const ReviewApproval = lazy(() => import("@/pages/ReviewApproval"));
const ProjectDetail = lazy(() => import("@/pages/ProjectDetail"));
const Projects = lazy(() => import("@/pages/Projects"));
const Settings = lazy(() => import("@/pages/Settings"));

const legacyPagePaths = {
  dashboard: "/dashboard",
  experiments: "/experiments/new",
  playground: "/playground",
  optimization: "/experiments",
  comparison: "/experiments",
  review: "/review",
  registry: "/prompts",
  settings: "/settings",
} as const;

function LoginRoute() {
  const {
    user,
    clearError,
    signInWithGoogle,
    signInWithEmail,
    registerWithEmail,
    sendPasswordReset,
    error,
  } = useAuth();
  const [, navigate] = useLocation();
  if (user) return <Redirect to="/dashboard" replace />;

  const runAndNavigate = async (action: () => Promise<void>) => {
    await action();
    navigate("/dashboard", { replace: true });
  };

  return (
    <Login
      onClearError={clearError}
      onGoogleSignIn={() => runAndNavigate(signInWithGoogle)}
      onEmailSignIn={(email, password) => runAndNavigate(() => signInWithEmail(email, password))}
      onRegister={(name, email, password) =>
        runAndNavigate(() => registerWithEmail(name, email, password))
      }
      onPasswordReset={sendPasswordReset}
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
  return <CreateExperiment />;
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
          <Route path="/projects">
            <Projects />
          </Route>
          <Route path="/projects/:projectId">
            <ProjectDetail />
          </Route>
          <Route path="/experiments">
            <Experiments />
          </Route>
          <Route path="/experiments/new">
            <CreateExperimentRoute />
          </Route>
          <Route path="/datasets">
            <Datasets />
          </Route>
          <Route path="/playground">
            <Playground />
          </Route>
          <Route path="/comparison-runs/:runId">
            <Comparison />
          </Route>
          <Route path="/optimization-runs/:runId">
            <OptimizationRun />
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
