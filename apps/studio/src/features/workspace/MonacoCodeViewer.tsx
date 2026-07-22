import Editor, { type OnMount } from "@monaco-editor/react";
import type { editor as MonacoEditor, Range as MonacoRange } from "monaco-editor";
import { useEffect, useRef } from "react";

import { configureMonaco } from "./monacoEnvironment";

configureMonaco();

export interface MonacoHighlight {
  startLine: number;
  endLine: number;
}

export interface MonacoCodeViewerProps {
  value: string;
  language: string;
  /** A line block to reveal and outline (e.g. a Vault search hit). */
  highlight?: MonacoHighlight | null;
}

const EDITOR_OPTIONS: MonacoEditor.IStandaloneEditorConstructionOptions = {
  readOnly: true,
  domReadOnly: true,
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  fontSize: 12,
  lineNumbers: "on",
  renderLineHighlight: "none",
  automaticLayout: true,
  wordWrap: "off",
  scrollbar: { alwaysConsumeMouseWheel: false },
};

/**
 * Read-only Monaco viewer for a single file. It shows syntax-highlighted text
 * and, when given a `highlight`, outlines that line block and scrolls it into
 * view. There is no editing, saving, multi-file tab, or language-service wiring
 * here — it is deliberately a viewer.
 */
export default function MonacoCodeViewer({
  value,
  language,
  highlight,
}: MonacoCodeViewerProps) {
  const editorRef = useRef<MonacoEditor.IStandaloneCodeEditor | null>(null);
  const rangeCtorRef = useRef<typeof MonacoRange | null>(null);
  const decorationsRef =
    useRef<MonacoEditor.IEditorDecorationsCollection | null>(null);

  const applyHighlight = () => {
    const editor = editorRef.current;
    const RangeCtor = rangeCtorRef.current;
    if (!editor || !RangeCtor) return;
    decorationsRef.current?.clear();
    if (!highlight) return;
    const lineCount = editor.getModel()?.getLineCount() ?? highlight.endLine;
    const start = clamp(highlight.startLine, 1, lineCount);
    const end = clamp(highlight.endLine, start, lineCount);
    decorationsRef.current = editor.createDecorationsCollection([
      {
        range: new RangeCtor(start, 1, end, 1),
        options: {
          isWholeLine: true,
          className: "workspace-editor__match-line",
          linesDecorationsClassName: "workspace-editor__match-gutter",
        },
      },
    ]);
    editor.revealLineInCenter(start);
  };

  const handleMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;
    rangeCtorRef.current = monaco.Range;
    applyHighlight();
  };

  // Re-apply when the file text or its highlight changes; the editor instance
  // and the stable `applyHighlight` closure are reused across those changes.
  useEffect(() => {
    applyHighlight();
  }, [value, highlight?.startLine, highlight?.endLine]);

  return (
    <div className="workspace-editor__monaco">
      <Editor
        value={value}
        language={language}
        theme="vs-dark"
        options={EDITOR_OPTIONS}
        onMount={handleMount}
        loading={<span className="workspace-editor__loading">Loading editor…</span>}
      />
    </div>
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(value, max));
}
