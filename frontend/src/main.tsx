import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource/ibm-plex-sans/latin-400.css";
import "@fontsource/ibm-plex-sans/latin-500.css";
import "@fontsource/ibm-plex-sans/latin-600.css";
import "@fontsource/source-serif-4/latin-400.css";
import "@fontsource/source-serif-4/latin-600.css";

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
