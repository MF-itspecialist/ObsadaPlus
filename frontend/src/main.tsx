import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { AuthProvider } from "./context/AuthContext";
import { PeriodProvider } from "./context/PeriodContext";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <PeriodProvider>
          <App />
        </PeriodProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
