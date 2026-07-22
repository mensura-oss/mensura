import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import editorWorker from "monaco-editor/esm/vs/editor/editor.worker?worker";
import cssWorker from "monaco-editor/esm/vs/language/css/css.worker?worker";
import htmlWorker from "monaco-editor/esm/vs/language/html/html.worker?worker";
import jsonWorker from "monaco-editor/esm/vs/language/json/json.worker?worker";
import tsWorker from "monaco-editor/esm/vs/language/typescript/ts.worker?worker";

/**
 * Point `@monaco-editor/react` at the locally bundled `monaco-editor` instead
 * of its default CDN loader, and wire language web-workers via Vite's `?worker`
 * imports. This keeps Studio fully offline (Tauri-friendly) and out of the CSP's
 * way. It is a browser-only side effect: this module is imported solely by
 * {@link MonacoCodeViewer}, which is lazy-loaded and mocked in tests, so the
 * heavy worker bundles never load in the test runner.
 */
let configured = false;

export function configureMonaco(): void {
  if (configured) return;
  configured = true;

  self.MonacoEnvironment = {
    getWorker(_workerId, label) {
      switch (label) {
        case "json":
          return new jsonWorker();
        case "css":
        case "scss":
        case "less":
          return new cssWorker();
        case "html":
        case "handlebars":
        case "razor":
          return new htmlWorker();
        case "typescript":
        case "javascript":
          return new tsWorker();
        default:
          return new editorWorker();
      }
    },
  };

  loader.config({ monaco });
}
