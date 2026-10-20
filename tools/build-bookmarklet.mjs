// Buduje tools/lnp-export.bookmarklet.txt (adres zakładki) z tools/lnp-export.js: node tools/build-bookmarklet.mjs
import { readFileSync, writeFileSync } from "node:fs";

const dir = new URL(".", import.meta.url);
const code = readFileSync(new URL("lnp-export.js", dir), "utf8")
  .split("\n")
  .filter((line) => !line.trim().startsWith("//"))
  .map((line) => line.replace(/\s+\/\/ .*$/, "").replace(/\/\* .*? \*\//g, "").trim())
  .filter(Boolean)
  .join("\n");
writeFileSync(new URL("lnp-export.bookmarklet.txt", dir), "javascript:" + encodeURIComponent(code) + "\n");
