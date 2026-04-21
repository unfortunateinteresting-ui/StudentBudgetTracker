import "@fontsource/newsreader/700.css";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";

import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./App";
import { applyThemeMode, readThemeMode } from "./lib/theme";
import "./styles/tokens.css";
import "./styles/global.css";

applyThemeMode(readThemeMode());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
