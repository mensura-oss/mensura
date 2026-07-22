/**
 * Map a file to a Monaco language id for read-only syntax highlighting.
 * Extension-driven (the most reliable signal); unknown files fall back to the
 * inventory's language label and finally to `plaintext`. This only affects
 * tokenisation — no language services, diagnostics, or IntelliSense.
 */

const EXTENSION_LANGUAGE: Record<string, string> = {
  ".ts": "typescript",
  ".mts": "typescript",
  ".cts": "typescript",
  ".tsx": "typescript",
  ".js": "javascript",
  ".mjs": "javascript",
  ".cjs": "javascript",
  ".jsx": "javascript",
  ".py": "python",
  ".rb": "ruby",
  ".rs": "rust",
  ".go": "go",
  ".java": "java",
  ".c": "c",
  ".h": "c",
  ".cc": "cpp",
  ".cpp": "cpp",
  ".hpp": "cpp",
  ".cs": "csharp",
  ".php": "php",
  ".swift": "swift",
  ".kt": "kotlin",
  ".sh": "shell",
  ".bash": "shell",
  ".sql": "sql",
  ".css": "css",
  ".scss": "scss",
  ".less": "less",
  ".html": "html",
  ".htm": "html",
  ".xml": "xml",
  ".json": "json",
  ".jsonc": "json",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".toml": "ini",
  ".ini": "ini",
  ".md": "markdown",
  ".mdx": "markdown",
  ".markdown": "markdown",
};

const LANGUAGE_LABEL_ALIAS: Record<string, string> = {
  typescript: "typescript",
  javascript: "javascript",
  python: "python",
  markdown: "markdown",
  json: "json",
  yaml: "yaml",
  rust: "rust",
  go: "go",
  java: "java",
  ruby: "ruby",
  shell: "shell",
  html: "html",
  css: "css",
};

function extensionOf(path: string): string {
  const name = path.slice(path.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  if (dot <= 0) return "";
  return name.slice(dot).toLowerCase();
}

export function monacoLanguageForFile(
  path: string,
  language: string | null,
): string {
  const byExtension = EXTENSION_LANGUAGE[extensionOf(path)];
  if (byExtension) return byExtension;
  if (language) {
    const alias = LANGUAGE_LABEL_ALIAS[language.toLowerCase()];
    if (alias) return alias;
  }
  return "plaintext";
}
