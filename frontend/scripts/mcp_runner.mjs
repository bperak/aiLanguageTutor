import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
// Lazy import Playwright only if browser navigation is actually needed.
let chromium = null;
async function ensureChromium() {
  if (chromium) return chromium;
  const mod = await import('playwright');
  chromium = mod.chromium;
  return chromium;
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function loadScenario(p) {
  const full = path.isAbsolute(p) ? p : path.resolve(__dirname, p);
  const text = fs.readFileSync(full, 'utf-8');
  return JSON.parse(text);
}

function evalInContext(expression, context) {
  // Evaluate an expression string with variables from context
  // Use Function constructor to avoid polluting global scope
  const fn = new Function('ctx', 'with (ctx) { return (' + expression + '); }');
  return fn(context);
}

async function runScenario(scenarioPath) {
  const scenario = loadScenario(scenarioPath);
  let browser = null;
  let context = null;
  let page = null;
  const saved = {};

  try {
    for (const [i, step] of scenario.steps.entries()) {
      const prefix = `[${scenario.name}] step ${i + 1}/${scenario.steps.length}`;
      if (step.action === 'navigate') {
        if (process.env.MCP_SKIP_BROWSER === '1') {
          console.warn(prefix, 'navigate skipped (MCP_SKIP_BROWSER=1)');
          continue;
        }
        if (!browser) {
          try {
            await ensureChromium();
            browser = await chromium.launch({ headless: true });
            context = await browser.newContext();
            page = await context.newPage();
          } catch (e) {
            console.warn(prefix, 'navigate unavailable (no browser); skipping', e?.message);
            continue;
          }
        }
        let url = step.url;
        if (process.env.TARGET_FRONTEND) {
          url = url.replace('http://localhost:3000', process.env.TARGET_FRONTEND);
        }
        try {
          await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
          console.log(prefix, 'navigate OK', url);
        } catch (e) {
          console.warn(prefix, 'navigate FAILED, falling back to about:blank', e?.message);
          if (page) await page.goto('about:blank');
        }
      } else if (step.action === 'evaluate') {
        let fnStr = step.function;
        if (process.env.TARGET_BACKEND) {
          fnStr = fnStr.replaceAll('http://localhost:8000', process.env.TARGET_BACKEND);
        }
        let result;
        if (/fetch\(/.test(fnStr) && !/document\.|window\./.test(fnStr)) {
          // Run network-only evaluates in Node context to avoid browser CORS/DNS issues
          const fn = eval(fnStr); // eslint-disable-line no-eval
          result = await fn();
        } else {
          if (!page) {
            // No browser available; treat as unsupported step
            throw new Error('Browser page not available for evaluate step');
          }
          result = await page.evaluate(async (code) => {
            const fn = eval(code); // eslint-disable-line no-eval
            const out = await fn();
            return out;
          }, fnStr);
        }
        if (step.saveAs) {
          saved[step.saveAs] = result;
        }
        console.log(prefix, 'evaluate OK', step.saveAs ? `saved as ${step.saveAs}` : '');
      } else if (step.action === 'assert') {
        const ok = !!evalInContext(step.expression, saved);
        if (!ok) {
          throw new Error(`Assertion failed: ${step.expression}`);
        }
        console.log(prefix, 'assert OK');
      } else {
        throw new Error(`Unknown action: ${step.action}`);
      }
    }
    if (browser) await browser.close();
    console.log(`[${scenario.name}] PASS`);
    return 0;
  } catch (err) {
    if (browser) await browser.close();
    console.error(`[${scenario.name}] FAIL:`, err?.message || String(err));
    return 1;
  }
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('Usage: node scripts/mcp_runner.mjs <scenario.json> [more.json ...]');
    process.exit(2);
  }
  let code = 0;
  for (const p of args) {
    const rc = await runScenario(p);
    if (rc !== 0) {
      code = rc;
    }
  }
  process.exit(code);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});


