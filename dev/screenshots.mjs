// README screenshots from the anonymised demo (dev/demo, made by dev/demo.py). Development only.
//
//   PLAYWRIGHT=/path/to/node_modules/playwright/index.mjs node dev/screenshots.mjs [month]
//
// Same slides, themes and sizes every time, so a release can refresh them in one go. Check the images before
// committing: they must only show demo data.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const { chromium } = await import(process.env.PLAYWRIGHT || "playwright");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const demo = path.join(root, "dev", "demo");
const out = path.join(root, "docs", "screenshots");
const months = fs.readdirSync(demo).filter((f) => /^\d{4}-\d{2}\.html$/.test(f)).sort();
const month = process.argv[2] || months.at(-1).slice(0, 7);
const year = fs.readdirSync(demo).filter((f) => /^year-\d{4}-\d{2}\.html$/.test(f)).sort().at(-1).slice(0, -5);

// [file name, page, slide, theme, width, height]
const SHOTS = [
  ["cover", month, "cover", "night"],
  ["summary", month, "story", "night"],
  ["electricity", month, "energy", "night"],
  ["costs-light", month, "cost", "light"],
  ["devices-light", month, "devices", "light"],
  ["heat-pump", month, "heatpump", "night"],
  ["car", month, "car", "night"],
  ["weather", month, "weather", "night"],
  ["indoor", month, "indoor", "night"],
  ["gas", month, "gas", "night"],
  ["own-figures", month, "custom", "night"],
  ["year-electricity", year, "energy", "night"],
  ["year-weather", year, "weather", "night"],
  ["mobile", month, "cover", "night", 390, 844],
];

const browser = await chromium.launch();
let made = 0;
for (const [name, page, slide, theme, w = 1440, h = 900] of SHOTS) {
  const file = path.join(demo, `${page}.html`);
  const p = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
  await p.goto(`${pathToFileURL(file).href}#s=${slide}&theme=${theme}`);
  await p.evaluate(() => document.fonts.ready);
  if (!(await p.$(`#${slide}`))) {
    console.log(`skip ${name}: no slide #${slide} in ${page}`);
    await p.close();
    continue;
  }
  await p.evaluate((id) => window.scrollTo({ top: document.getElementById(id).offsetTop, behavior: "instant" }), slide);
  await p.waitForTimeout(400);
  await p.screenshot({ path: path.join(out, `${name}.png`) });
  await p.close();
  made++;
}
await browser.close();
console.log(`${made} screenshots written to ${out} (month ${month}, ${year})`);
