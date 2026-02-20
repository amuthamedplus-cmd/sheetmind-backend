import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { ErrorBoundary } from "./components/ErrorBoundary";
import "./styles/index.css";
import { initAnalytics, endSession } from "./services/analytics";

// Initialize PostHog analytics
initAnalytics();

// Track session end when tab/window closes
window.addEventListener("beforeunload", () => {
  endSession();
});

// Catch unhandled promise rejections (not caught by React ErrorBoundary)
window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason instanceof Error ? event.reason.message : String(event.reason);
  console.error("[Unhandled Rejection]", reason);
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
