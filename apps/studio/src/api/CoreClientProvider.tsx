import { createContext, useContext, type PropsWithChildren } from "react";

import { coreClient, type CoreClient } from "./coreClient";

const CoreClientContext = createContext<CoreClient | null>(null);

export function CoreClientProvider({
  children,
  client = coreClient,
}: PropsWithChildren<{ client?: CoreClient }>) {
  return (
    <CoreClientContext.Provider value={client}>
      {children}
    </CoreClientContext.Provider>
  );
}

export function useCoreClient() {
  const client = useContext(CoreClientContext);

  if (!client) {
    throw new Error("useCoreClient must be used inside CoreClientProvider");
  }

  return client;
}
