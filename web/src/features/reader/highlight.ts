import { createHighlighterCore } from "shiki/core";
let highlighter: ReturnType<typeof createHighlighterCore> | undefined;
export async function highlightCode(code: string, language: string) {
  highlighter ??= createHighlighterCore({
    themes: [import("shiki/themes/github-light.mjs")],
    langs: [
      import("shiki/langs/python.mjs"),
      import("shiki/langs/markdown.mjs"),
      import("shiki/langs/yaml.mjs"),
      import("shiki/langs/json.mjs"),
      import("shiki/langs/toml.mjs"),
      import("shiki/langs/shellscript.mjs"),
    ],
    loadWasm: import("shiki/wasm"),
  });
  const h = await highlighter;
  const lang = language === "shell" ? "shellscript" : language;
  return h.codeToTokens(code, {
    lang: h.getLoadedLanguages().includes(lang) ? lang : "text",
    theme: "github-light",
  }).tokens;
}
