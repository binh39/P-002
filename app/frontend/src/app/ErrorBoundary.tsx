import { Component, type ErrorInfo, type ReactNode } from "react";

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends Component<
  {
    children: ReactNode;
  },
  State
> {
  state: State = { hasError: false };
  static getDerivedStateFromError(): State {
    return { hasError: true };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("PromptOpt UI crashed", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="fatal-error" role="alert">
          <div>
            <span className="eyebrow">Unexpected error</span>
            <h1>PromptOpt could not render this page.</h1>
            <p>
              Reload the application. If the problem continues, share the time of the error with the
              team.
            </p>
            <button onClick={() => window.location.reload()}>Reload application</button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
