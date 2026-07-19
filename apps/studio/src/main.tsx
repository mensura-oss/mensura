import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";

import { CoreClientProvider } from "./api/CoreClientProvider";
import { App } from "./app/App";
import { createStudioQueryClient } from "./app/queryClient";
import "./styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Mensura Studio root element was not found");
}

const queryClient = createStudioQueryClient();

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <CoreClientProvider>
        <App />
      </CoreClientProvider>
    </QueryClientProvider>
  </StrictMode>,
);
