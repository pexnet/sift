import React from "react";
import ReactDOM from "react-dom/client";

import { AppRouterProvider } from "./app/router";
import "./app/styles.css";

const rootElement = document.getElementById("sift-app-root");
if (!rootElement) {
  throw new Error("Missing root element #sift-app-root");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <AppRouterProvider />
  </React.StrictMode>
);
