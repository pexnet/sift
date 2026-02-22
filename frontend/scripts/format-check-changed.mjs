import { execSync, spawnSync } from "node:child_process";

const baseRef = process.env.FORMAT_BASE_REF ?? "origin/develop";
const fallbackRange = "HEAD~1...HEAD";

function readChangedFiles(range) {
  try {
    const raw = execSync(`git diff --name-only --diff-filter=ACMRT ${range}`, {
      encoding: "utf8",
      stdio: ["ignore", "pipe", "ignore"],
    });
    return raw
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

let changedFiles = readChangedFiles(`${baseRef}...HEAD`);
if (changedFiles.length === 0) {
  changedFiles = readChangedFiles(fallbackRange);
}

const checkableExtensions = [".ts", ".tsx", ".js", ".jsx", ".css", ".json", ".md", ".html", ".yml", ".yaml"];
const checkableFiles = changedFiles
  .filter((filePath) => filePath.startsWith("frontend/"))
  .filter((filePath) => checkableExtensions.some((extension) => filePath.endsWith(extension)))
  .filter((filePath) => !filePath.startsWith("frontend/node_modules/"))
  .filter((filePath) => !filePath.startsWith("frontend/dist/"));

if (checkableFiles.length === 0) {
  console.log("No changed frontend files require Prettier check.");
  process.exit(0);
}

console.log(`Checking Prettier formatting for ${checkableFiles.length} changed frontend file(s).`);
const result = spawnSync("pnpm", ["exec", "prettier", "--check", ...checkableFiles], {
  stdio: "inherit",
  shell: true,
});

if (typeof result.status === "number") {
  process.exit(result.status);
}

process.exit(1);
