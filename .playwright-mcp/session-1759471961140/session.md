
### Tool call: browser_navigate
- Args
```json
{
  "url": "http://localhost:3000/lexical/graph"
}
```
- Code
```js
await page.goto('http://localhost:3000/lexical/graph');
```
- Snapshot: 001.snapshot.yml


### Tool call: browser_network_requests
- Args
```json
{}
```
- Result
```
[GET] http://localhost:3000/lexical/graph => [200] OK
[GET] http://localhost:3000/_next/static/media/4cf2300e9c8272f7-s.p.woff2 => [200] OK
[GET] http://localhost:3000/_next/static/media/93f479601ee12b01-s.p.woff2 => [200] OK
[GET] http://localhost:3000/_next/static/css/app/layout.css?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/webpack.js?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/main-app.js?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app-pages-internals.js => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app/layout.js => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app/lexical/graph/page.js => [200] OK
[GET] http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji => [500] Internal Server Error
[GET] http://localhost:3000/_next/static/chunks/_app-pages-browser_node_modules_react-force-graph-2d_dist_react-force-graph-2d_mjs.js => [200] OK
```


### Tool call: browser_console_messages
- Args
```json
{
  "onlyErrors": false
}
```
- Result
```
[INFO] %cDownload the React DevTools for a better development experience: https://react.dev/link/react-devtools font-weight:bold @ webpack-internal:///(app-pages-browser)/./node_modules/next/dist/compiled/react-dom/cjs/react-dom-client.development.js:25630
[LOG] Detected Japanese (kanji/katakana) input: 日本 @ webpack-internal:///(app-pages-browser)/./src/app/lexical/graph/page.tsx:94
[LOG] Detected Japanese (kanji/katakana) input: 日本 @ webpack-internal:///(app-pages-browser)/./src/app/lexical/graph/page.tsx:94
[LOG] Detected Japanese (kanji/katakana) input: 日本 @ webpack-internal:///(app-pages-browser)/./src/app/lexical/graph/page.tsx:94
[LOG] Detected Japanese (kanji/katakana) input: 日本 @ webpack-internal:///(app-pages-browser)/./src/app/lexical/graph/page.tsx:94
[LOG] Detected Japanese (kanji/katakana) input: 日本 @ webpack-internal:///(app-pages-browser)/./src/app/lexical/graph/page.tsx:94
[LOG] LexicalGraph2D: Node data changed {selectedNode: null, neighbors: Array(0)} @ webpack-internal:///(app-pages-browser)/./src/components/lexical/LexicalGraph2D.tsx:149
[LOG] Fetching graph data from: /api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji @ webpack-internal:///(app-pages-browser)/./src/components/lexical/LexicalGraph2D.tsx:183
[ERROR] Failed to load resource: the server responded with a status of 500 (Internal Server Error) @ http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji:0
```


### Tool call: browser_take_screenshot
- Args
```json
{
  "type": "png",
  "fullPage": true
}
```
- Result
```
Took the full page screenshot and saved it as d:\My_apps\aiLanguageTutor\.playwright-mcp\page-2025-10-03T06-12-58-274Z.png
```
- Code
```js
// Screenshot full page and save it as d:\My_apps\aiLanguageTutor\.playwright-mcp\page-2025-10-03T06-12-58-274Z.png
await page.screenshot({
fullPage: true,
  path: 'd:\\My_apps\\aiLanguageTutor\\.playwright-mcp\\page-2025-10-03T06-12-58-274Z.png',
  scale: 'css',
  type: 'png'
});
```


### Tool call: browser_wait_for
- Args
```json
{
  "time": 1
}
```
- Result
```
Waited for 1
```
- Code
```js
await new Promise(f => setTimeout(f, 1 * 1000));
```
- Snapshot: 005.snapshot.yml


### Tool call: browser_evaluate
- Args
```json
{
  "function": "() => fetch('http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji').then(async r => ({ ok: r.ok, status: r.status, text: await r.text() })).catch(e => ({ ok: false, error: String(e) }))",
  "element": "Fetch backend response JSON for the failing endpoint"
}
```
- Result
```
{
  "ok": false,
  "status": 500,
  "text": "{\"detail\":\"{code: Neo.ClientError.Statement.SyntaxError} {message: Importing WITH should consist only of simple references to outside variables. Aliasing or expressions are not supported. (line 9, column 7 (offset: 289))\\n\\\"      WITH t, n1s, $depth AS depth, $limit2 AS limit2\\\"\\n       ^}\"}"
}
```
- Code
```js
await page.evaluate('() => fetch(\'http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji\').then(async r => ({ ok: r.ok, status: r.status, text: await r.text() })).catch(e => ({ ok: false, error: String(e) }))');
```
- Snapshot: 006.snapshot.yml


### Tool call: browser_evaluate
- Args
```json
{
  "function": "() => fetch('http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji').then(async r => ({ ok: r.ok, status: r.status, text: await r.text() })).catch(e => ({ ok: false, error: String(e) }))",
  "element": "Re-check backend response after fix"
}
```
- Result
```
{
  "ok": true,
  "status": 200,
  "text": "{\"nodes\":[{\"kanji\":\"日本\",\"hiragana\":\"にほん\",\"translation\":\"Japan\",\"level\":null,\"domain\":null,\"pos\":null,\"id\":\"日本\"},{\"id\":\"日の丸\",\"level\":null,\"hiragana\":\"ひのまる\",\"translation\":\"Rising Sun Flag\",\"name\":\"日の丸\",\"domain\":null,\"pos\":null}],\"links\":[{\"weight\":0.7,\"source\":\"日の丸\",\"target\":\"日本\"},{\"weight\":0.7,\"source\":\"日本\",\"target\":\"日の丸\"}],\"center\":{\"id\":\"日本\"}}"
}
```
- Code
```js
await page.evaluate('() => fetch(\'http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji\').then(async r => ({ ok: r.ok, status: r.status, text: await r.text() })).catch(e => ({ ok: false, error: String(e) }))');
```
- Snapshot: 007.snapshot.yml


### Tool call: browser_click
- Args
```json
{
  "element": "Search button on the lexical graph page",
  "ref": "e24"
}
```
- Code
```js
await page.getByRole('button', { name: 'Search' }).click();
```
- Snapshot: 008.snapshot.yml


### Tool call: browser_network_requests
- Args
```json
{}
```
- Result
```
[GET] http://localhost:3000/lexical/graph => [200] OK
[GET] http://localhost:3000/_next/static/media/4cf2300e9c8272f7-s.p.woff2 => [200] OK
[GET] http://localhost:3000/_next/static/media/93f479601ee12b01-s.p.woff2 => [200] OK
[GET] http://localhost:3000/_next/static/css/app/layout.css?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/webpack.js?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/main-app.js?v=1759471963013 => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app-pages-internals.js => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app/layout.js => [200] OK
[GET] http://localhost:3000/_next/static/chunks/app/lexical/graph/page.js => [200] OK
[GET] http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji => [500] Internal Server Error
[GET] http://localhost:3000/_next/static/chunks/_app-pages-browser_node_modules_react-force-graph-2d_dist_react-force-graph-2d_mjs.js => [200] OK
[GET] http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji => [500] Internal Server Error
[GET] http://localhost:8000/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji => [200] OK
```


### Tool call: browser_take_screenshot
- Args
```json
{
  "type": "png",
  "fullPage": true
}
```
- Result
```
Took the full page screenshot and saved it as d:\My_apps\aiLanguageTutor\.playwright-mcp\page-2025-10-03T06-25-03-979Z.png
```
- Code
```js
// Screenshot full page and save it as d:\My_apps\aiLanguageTutor\.playwright-mcp\page-2025-10-03T06-25-03-979Z.png
await page.screenshot({
fullPage: true,
  path: 'd:\\My_apps\\aiLanguageTutor\\.playwright-mcp\\page-2025-10-03T06-25-03-979Z.png',
  scale: 'css',
  type: 'png'
});
```


### User action: navigate
- Args
```json
{
  "name": "navigate",
  "url": "http://localhost:3000/lexical/graph"
}
```
- Code
```js
await page.goto('http://localhost:3000/lexical/graph');
```
- Snapshot: 011.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 012.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 013.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "bottle"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('bottle');
```
- Snapshot: 014.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 417,
    "y": 270
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 417,
      y: 270
    }
  });
```
- Snapshot: 015.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e131",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Open issues overlay' }).click();
```
- Snapshot: 016.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e167",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Copy Error Info' }).click();
```
- Snapshot: 017.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e1",
  "key": "ArrowLeft",
  "modifiers": 1
}
```
- Code
```js
await page.getByText('Skip to contentAI Language').press('Alt+ArrowLeft');
```
- Snapshot: 018.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e137",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('nextjs-portal > div > div').first().click();
```
- Snapshot: 019.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 020.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 021.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mother"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mother');
```
- Snapshot: 022.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e268",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Fit' }).click();
```
- Snapshot: 023.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 588,
    "y": 371
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 588,
      y: 371
    }
  });
```
- Snapshot: 024.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e274",
  "button": "left",
  "modifiers": 0,
  "clickCount": 2
}
```
- Code
```js
await page.locator('div').filter({ hasText: 'Loading new graph...' }).nth(5).dblclick();
```
- Snapshot: 025.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e38",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: '⚙️ Settings' }).click();
```
- Snapshot: 026.snapshot.yml


### User action: check
- Args
```json
{
  "name": "check",
  "ref": "e298"
}
```
- Code
```js
await page.getByRole('checkbox', { name: 'Exact Match' }).check();
```
- Snapshot: 027.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 028.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 029.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mot"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mot');
```
- Snapshot: 030.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mothe"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mothe');
```
- Snapshot: 031.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mother"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mother');
```
- Snapshot: 032.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 257,
    "y": 418
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 257,
      y: 418
    }
  });
```
- Snapshot: 033.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e131",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Open issues overlay' }).click();
```
- Snapshot: 034.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e474",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Copy Error Info' }).click();
```
- Snapshot: 035.snapshot.yml


### Tool call: browser_evaluate
- Args
```json
{
  "function": "() => fetch('/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji').then(r=>r.status)"
}
```
- Result
```
404
```
- Code
```js
await page.evaluate('() => fetch(\'/api/v1/lexical/graph?center=%E6%97%A5%E6%9C%AC&depth=1&searchField=kanji\').then(r=>r.status)');
```
- Snapshot: 036.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 445,
    "y": 294
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 445,
      y: 294
    }
  });
```
- Snapshot: 037.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 649,
    "y": 244
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 649,
      y: 244
    }
  });
```
- Snapshot: 038.snapshot.yml


### User action: openPage
- Args
```json
{
  "name": "openPage",
  "url": "chrome://new-tab-page/"
}
```
- Snapshot: 039.snapshot.yml


### User action: navigate
- Args
```json
{
  "name": "navigate",
  "url": "http://localhost:3000/lexical/graph"
}
```
- Code
```js
await page.goto('http://localhost:3000/lexical/graph');
```
- Snapshot: 040.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 041.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 042.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mother"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mother');
```
- Snapshot: 043.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 408,
    "y": 220
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 408,
      y: 220
    }
  });
```
- Snapshot: 044.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e24",
  "key": "F5",
  "modifiers": 2
}
```
- Code
```js
await page.locator('#main-content').press('ControlOrMeta+F5');
```
- Snapshot: 045.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 367,
    "y": 290
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 367,
      y: 290
    }
  });
```
- Snapshot: 046.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 282,
    "y": 267
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 282,
      y: 267
    }
  });
```
- Snapshot: 047.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 186,
    "y": 379
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 186,
      y: 379
    }
  });
```
- Snapshot: 048.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 270,
    "y": 173
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 270,
      y: 173
    }
  });
```
- Snapshot: 049.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 050.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 051.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "father"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('father');
```
- Snapshot: 052.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 337,
    "y": 135
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 337,
      y: 135
    }
  });
```
- Snapshot: 053.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e412",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Open issues overlay' }).click();
```
- Snapshot: 054.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e451",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Copy Error Info' }).click();
```
- Snapshot: 055.snapshot.yml


### Tool call: browser_evaluate
- Args
```json
{
  "function": "() => fetch('http://localhost:8000/api/v1/lexical/graph?center=%E7%A5%96%E7%88%B6&depth=1&searchField=translation').then(async r => ({ status: r.status, text: await r.text() }))"
}
```
- Result
```
{
  "status": 200,
  "text": "{\"nodes\":[{\"kanji\":\"祖父\",\"hiragana\":\"そふ\",\"translation\":\"grandfather\",\"level\":null,\"domain\":null,\"pos\":null,\"id\":\"祖父\"},{\"id\":\"おじいちゃん\",\"level\":null,\"hiragana\":null,\"translation\":\"Grandpa\",\"name\":\"おじいちゃん\",\"domain\":null,\"pos\":null},{\"id\":\"爺\",\"level\":null,\"hiragana\":\"じい\",\"translation\":\"old man\",\"name\":\"爺\",\"domain\":null,\"pos\":null},{\"id\":\"お爺\",\"level\":null,\"hiragana\":\"おじい\",\"translation\":\"grandfather\",\"name\":\"お爺\",\"domain\":null,\"pos\":null},{\"id\":\"お爺様\",\"level\":null,\"hiragana\":\"おじいさま\",\"translation\":\"grandfather\",\"name\":\"お爺様\",\"domain\":null,\"pos\":null},{\"id\":\"爺ちゃん\",\"level\":null,\"hiragana\":\"じいちゃん\",\"translation\":\"grandpa\",\"name\":\"爺ちゃん\",\"domain\":null,\"pos\":null},{\"id\":\"爺さん\",\"level\":null,\"hiragana\":\"じいさん\",\"translation\":\"grandfather\",\"name\":\"爺さん\",\"domain\":null,\"pos\":null},{\"id\":\"伯母\",\"level\":null,\"hiragana\":\"おば\",\"translation\":\"aunt\",\"name\":\"伯母\",\"domain\":null,\"pos\":null},{\"id\":\"お爺ちゃん\",\"level\":null,\"hiragana\":\"おじいちゃん\",\"translation\":\"grandpa\",\"name\":\"お爺ちゃん\",\"domain\":null,\"pos\":null},{\"id\":\"お爺さん\",\"level\":null,\"hiragana\":\"おじいさん\",\"translation\":\"grandfather\",\"name\":\"お爺さん\",\"domain\":null,\"pos\":null},{\"id\":\"おじいさん\",\"level\":null,\"hiragana\":\"おじいさん\",\"translation\":\"grandfather\",\"name\":\"おじいさん\",\"domain\":null,\"pos\":null},{\"id\":\"祖母\",\"level\":null,\"hiragana\":\"そぼ\",\"translation\":\"grandmother\",\"name\":\"祖母\",\"domain\":null,\"pos\":null},{\"id\":\"家族\",\"level\":null,\"hiragana\":\"かぞく\",\"translation\":\"family\",\"name\":\"家族\",\"domain\":null,\"pos\":null},{\"id\":\"親\",\"level\":null,\"hiragana\":\"おや\",\"translation\":\"parent\",\"name\":\"親\",\"domain\":null,\"pos\":null},{\"id\":\"父\",\"level\":null,\"hiragana\":\"ちち\",\"translation\":\"father\",\"name\":\"父\",\"domain\":null,\"pos\":null},{\"id\":\"従兄弟\",\"level\":null,\"hiragana\":\"いとこ\",\"translation\":\"cousin\",\"name\":\"従兄弟\",\"domain\":null,\"pos\":null},{\"id\":\"祖先\",\"level\":null,\"hiragana\":\"そせん\",\"translation\":\"ancestor\",\"name\":\"祖先\",\"domain\":null,\"pos\":null},{\"id\":\"先祖\",\"level\":null,\"hiragana\":\"せんぞ\",\"translation\":\"ancestor\",\"name\":\"先祖\",\"domain\":null,\"pos\":null},{\"id\":\"親戚\",\"level\":null,\"hiragana\":\"しんせき\",\"translation\":\"relative\",\"name\":\"親戚\",\"domain\":null,\"pos\":null},{\"id\":\"祖宗\",\"level\":null,\"hiragana\":\"そそう\",\"translation\":\"ancestor\",\"name\":\"祖宗\",\"domain\":null,\"pos\":null},{\"id\":\"孫息子\",\"level\":null,\"hiragana\":\"まごむすこ\",\"translation\":\"grandson\",\"name\":\"孫息子\",\"domain\":null,\"pos\":null},{\"id\":\"老父\",\"level\":null,\"hiragana\":\"ろうふ\",\"translation\":\"old father\",\"name\":\"老父\",\"domain\":null,\"pos\":null},{\"id\":\"従姉\",\"level\":null,\"hiragana\":\"じゅうし\",\"translation\":\"cousin (older female)\",\"name\":\"従姉\",\"domain\":null,\"pos\":null},{\"id\":\"従弟\",\"level\":null,\"hiragana\":\"じゅうてい\",\"translation\":\"cousin\",\"name\":\"従弟\",\"domain\":null,\"pos\":null},{\"id\":\"縁者\",\"level\":null,\"hiragana\":\"えんじゃ\",\"translation\":\"relative\",\"name\":\"縁者\",\"domain\":null,\"pos\":null},{\"id\":\"祖父母\",\"level\":null,\"hiragana\":\"そふぼ\",\"translation\":\"grandparents\",\"name\":\"祖父母\",\"domain\":null,\"pos\":null}],\"links\":[{\"weight\":0.85,\"source\":\"おじいちゃん\",\"target\":\"おじいさん\"},{\"weight\":0.95,\"source\":\"祖父\",\"target\":\"おじいさん\"},{\"weight\":0.7,\"source\":\"祖父母\",\"target\":\"おじいさん\"},{\"weight\":0.85,\"source\":\"おじいさん\",\"target\":\"おじいちゃん\"},{\"weight\":0.9,\"source\":\"祖父\",\"target\":\"おじいちゃん\"},{\"weight\":0.4,\"source\":\"親\",\"target\":\"伯母\"},{\"weight\":0.5,\"source\":\"家族\",\"target\":\"伯母\"},{\"weight\":0.2,\"source\":\"祖父\",\"target\":\"伯母\"},{\"weight\":0.2,\"source\":\"祖母\",\"target\":\"伯母\"},{\"weight\":0.3,\"source\":\"従兄弟\",\"target\":\"伯母\"},{\"weight\":0.6,\"source\":\"親戚\",\"target\":\"伯母\"},{\"weight\":0.55,\"source\":\"家族\",\"target\":\"親\"},{\"weight\":0.25,\"source\":\"祖父\",\"target\":\"親\"},{\"weight\":0.85,\"source\":\"父\",\"target\":\"親\"},{\"weight\":0.2,\"source\":\"親戚\",\"target\":\"親\"},{\"weight\":0.6,\"source\":\"祖父母\",\"target\":\"親\"},{\"weight\":0.75,\"source\":\"縁者\",\"target\":\"親\"},{\"weight\":0.4,\"source\":\"伯母\",\"target\":\"親\"},{\"weight\":0.2,\"source\":\"祖父\",\"target\":\"家族\"},{\"weight\":0.8,\"source\":\"親戚\",\"target\":\"家族\"},{\"weight\":0.45,\"source\":\"孫息子\",\"target\":\"家族\"},{\"weight\":0.7,\"source\":\"祖宗\",\"target\":\"家族\"},{\"weight\":0.1,\"source\":\"従弟\",\"target\":\"家族\"},{\"weight\":0.85,\"source\":\"縁者\",\"target\":\"家族\"},{\"weight\":0.5,\"source\":\"祖父母\",\"target\":\"家族\"},{\"weight\":0.5,\"source\":\"伯母\",\"target\":\"家族\"},{\"weight\":0.55,\"source\":\"親\",\"target\":\"家族\"},{\"weight\":0.5,\"source\":\"孫息子\",\"target\":\"親戚\"},{\"weight\":0.75,\"source\":\"従姉\",\"target\":\"親戚\"},{\"weight\":0.85,\"source\":\"従弟\",\"target\":\"親戚\"},{\"weight\":0.95,\"source\":\"縁者\",\"target\":\"親戚\"},{\"weight\":0.4,\"source\":\"祖父母\",\"target\":\"親戚\"},{\"weight\":0.8,\"source\":\"家族\",\"target\":\"親戚\"},{\"weight\":0.15,\"source\":\"祖父\",\"target\":\"親戚\"},{\"weight\":0.6,\"source\":\"伯母\",\"target\":\"親戚\"},{\"weight\":0.65,\"source\":\"従兄弟\",\"target\":\"親戚\"},{\"weight\":0.2,\"source\":\"親\",\"target\":\"親戚\"},{\"weight\":0.95,\"source\":\"祖先\",\"target\":\"先祖\"},{\"weight\":0.1,\"source\":\"祖父\",\"target\":\"先祖\"},{\"weight\":0.95,\"source\":\"祖宗\",\"target\":\"先祖\"},{\"weight\":0.8,\"source\":\"祖父母\",\"target\":\"先祖\"},{\"weight\":0.7,\"source\":\"祖父\",\"target\":\"祖先\"},{\"weight\":0.7,\"source\":\"祖母\",\"target\":\"祖先\"},{\"weight\":0.95,\"source\":\"先祖\",\"target\":\"祖先\"},{\"weight\":0.9,\"source\":\"祖宗\",\"target\":\"祖先\"},{\"weight\":0.3,\"source\":\"祖父母\",\"target\":\"祖先\"},{\"weight\":0.9,\"source\":\"おじいちゃん\",\"target\":\"祖父\"},{\"weight\":0.85,\"source\":\"爺\",\"target\":\"祖父\"},{\"weight\":0.65,\"source\":\"お爺\",\"target\":\"祖父\"},{\"weight\":0.7,\"source\":\"お爺様\",\"target\":\"祖父\"},{\"weight\":0.75,\"source\":\"爺ちゃん\",\"target\":\"祖父\"},{\"weight\":0.8,\"source\":\"爺さん\",\"target\":\"祖父\"},{\"weight\":0.2,\"source\":\"伯母\",\"target\":\"祖父\"},{\"weight\":0.9,\"source\":\"お爺ちゃん\",\"target\":\"祖父\"},{\"weight\":0.95,\"source\":\"お爺さん\",\"target\":\"祖父\"},{\"weight\":0.95,\"source\":\"おじいさん\",\"target\":\"祖父\"},{\"weight\":0.5,\"source\":\"祖母\",\"target\":\"祖父\"},{\"weight\":0.2,\"source\":\"家族\",\"target\":\"祖父\"},{\"weight\":0.25,\"source\":\"親\",\"target\":\"祖父\"},{\"weight\":0.3,\"source\":\"父\",\"target\":\"祖父\"},{\"weight\":0.6,\"source\":\"従兄弟\",\"target\":\"祖父\"},{\"weight\":0.7,\"source\":\"祖先\",\"target\":\"祖父\"},{\"weight\":0.1,\"source\":\"先祖\",\"target\":\"祖父\"},{\"weight\":0.15,\"source\":\"親戚\",\"target\":\"祖父\"},{\"weight\":0.8,\"source\":\"祖宗\",\"target\":\"祖父\"},{\"weight\":0.25,\"source\":\"孫息子\",\"target\":\"祖父\"},{\"weight\":0.65,\"source\":\"老父\",\"target\":\"祖父\"},{\"weight\":0.35,\"source\":\"従姉\",\"target\":\"祖父\"},{\"weight\":0.4,\"source\":\"従弟\",\"target\":\"祖父\"},{\"weight\":0.5,\"source\":\"縁者\",\"target\":\"祖父\"},{\"weight\":0.8,\"source\":\"祖父母\",\"target\":\"祖父\"},{\"weight\":0.3,\"source\":\"祖先\",\"target\":\"祖父母\"},{\"weight\":0.7,\"source\":\"おじいさん\",\"target\":\"祖父母\"},{\"weight\":0.85,\"source\":\"祖宗\",\"target\":\"祖父母\"},{\"weight\":0.4,\"source\":\"親戚\",\"target\":\"祖父母\"},{\"weight\":0.8,\"source\":\"祖父\",\"target\":\"祖父母\"},{\"weight\":0.5,\"source\":\"家族\",\"target\":\"祖父母\"},{\"weight\":0.6,\"source\":\"親\",\"target\":\"祖父母\"},{\"weight\":0.8,\"source\":\"祖母\",\"target\":\"祖父母\"},{\"weight\":0.8,\"source\":\"先祖\",\"target\":\"祖父母\"},{\"weight\":0.2,\"source\":\"伯母\",\"target\":\"祖母\"},{\"weight\":0.5,\"source\":\"祖父\",\"target\":\"祖母\"},{\"weight\":0.6,\"source\":\"従兄弟\",\"target\":\"祖母\"},{\"weight\":0.7,\"source\":\"祖先\",\"target\":\"祖母\"},{\"weight\":0.8,\"source\":\"祖宗\",\"target\":\"祖母\"},{\"weight\":0.2,\"source\":\"孫息子\",\"target\":\"祖母\"},{\"weight\":0.4,\"source\":\"従姉\",\"target\":\"祖母\"},{\"weight\":0.35,\"source\":\"従弟\",\"target\":\"祖母\"},{\"weight\":0.45,\"source\":\"縁者\",\"target\":\"祖母\"},{\"weight\":0.8,\"source\":\"祖父母\",\"target\":\"祖母\"},{\"weight\":0.3,\"source\":\"祖父\",\"target\":\"父\"},{\"weight\":0.85,\"source\":\"親\",\"target\":\"父\"},{\"weight\":0.15,\"source\":\"孫息子\",\"target\":\"父\"},{\"weight\":0.3,\"source\":\"従弟\",\"target\":\"父\"},{\"weight\":0.85,\"source\":\"家族\",\"target\":\"縁者\"},{\"weight\":0.45,\"source\":\"祖母\",\"target\":\"縁者\"},{\"weight\":0.65,\"source\":\"従兄弟\",\"target\":\"縁者\"},{\"weight\":0.95,\"source\":\"親戚\",\"target\":\"縁者\"},{\"weight\":0.5,\"source\":\"祖父\",\"target\":\"縁者\"},{\"weight\":0.75,\"source\":\"親\",\"target\":\"縁者\"},{\"weight\":0.1,\"source\":\"家族\",\"target\":\"従弟\"},{\"weight\":0.4,\"source\":\"祖父\",\"target\":\"従弟\"},{\"weight\":0.85,\"source\":\"親戚\",\"target\":\"従弟\"},{\"weight\":0.3,\"source\":\"父\",\"target\":\"従弟\"},{\"weight\":0.35,\"source\":\"祖母\",\"target\":\"従弟\"},{\"weight\":0.8,\"source\":\"従姉\",\"target\":\"従弟\"},{\"weight\":0.95,\"source\":\"従兄弟\",\"target\":\"従弟\"},{\"weight\":0.4,\"source\":\"祖母\",\"target\":\"従姉\"},{\"weight\":0.9,\"source\":\"従兄弟\",\"target\":\"従姉\"},{\"weight\":0.75,\"source\":\"親戚\",\"target\":\"従姉\"},{\"weight\":0.35,\"source\":\"祖父\",\"target\":\"従姉\"},{\"weight\":0.8,\"source\":\"従弟\",\"target\":\"従姉\"},{\"weight\":0.55,\"source\":\"爺\",\"target\":\"老父\"},{\"weight\":0.55,\"source\":\"お爺さん\",\"target\":\"老父\"},{\"weight\":0.65,\"source\":\"祖父\",\"target\":\"老父\"},{\"weight\":0.8,\"source\":\"祖母\",\"target\":\"祖宗\"},{\"weight\":0.8,\"source\":\"祖父\",\"target\":\"祖宗\"},{\"weight\":0.9,\"source\":\"祖先\",\"target\":\"祖宗\"},{\"weight\":0.95,\"source\":\"先祖\",\"target\":\"祖宗\"},{\"weight\":0.7,\"source\":\"家族\",\"target\":\"祖宗\"},{\"weight\":0.85,\"source\":\"祖父母\",\"target\":\"祖宗\"},{\"weight\":0.15,\"source\":\"父\",\"target\":\"孫息子\"},{\"weight\":0.45,\"source\":\"家族\",\"target\":\"孫息子\"},{\"weight\":0.3,\"source\":\"従兄弟\",\"target\":\"孫息子\"},{\"weight\":0.25,\"source\":\"祖父\",\"target\":\"孫息子\"},{\"weight\":0.2,\"source\":\"祖母\",\"target\":\"孫息子\"},{\"weight\":0.5,\"source\":\"親戚\",\"target\":\"孫息子\"},{\"weight\":0.65,\"source\":\"縁者\",\"target\":\"従兄弟\"},{\"weight\":0.95,\"source\":\"従弟\",\"target\":\"従兄弟\"},{\"weight\":0.9,\"source\":\"従姉\",\"target\":\"従兄弟\"},{\"weight\":0.3,\"source\":\"孫息子\",\"target\":\"従兄弟\"},{\"weight\":0.65,\"source\":\"親戚\",\"target\":\"従兄弟\"},{\"weight\":0.3,\"source\":\"伯母\",\"target\":\"従兄弟\"},{\"weight\":0.6,\"source\":\"祖父\",\"target\":\"従兄弟\"},{\"weight\":0.6,\"source\":\"祖母\",\"target\":\"従兄弟\"},{\"weight\":0.75,\"source\":\"爺さん\",\"target\":\"爺\"},{\"weight\":0.9,\"source\":\"お爺さん\",\"target\":\"爺\"},{\"weight\":0.85,\"source\":\"祖父\",\"target\":\"爺\"},{\"weight\":0.55,\"source\":\"老父\",\"target\":\"爺\"},{\"weight\":0.9,\"source\":\"爺\",\"target\":\"お爺さん\"},{\"weight\":0.95,\"source\":\"祖父\",\"target\":\"お爺さん\"},{\"weight\":0.55,\"source\":\"老父\",\"target\":\"お爺さん\"},{\"weight\":0.75,\"source\":\"爺\",\"target\":\"爺さん\"},{\"weight\":0.8,\"source\":\"祖父\",\"target\":\"爺さん\"},{\"weight\":0.9,\"source\":\"祖父\",\"target\":\"お爺ちゃん\"},{\"weight\":0.75,\"source\":\"祖父\",\"target\":\"爺ちゃん\"},{\"weight\":0.7,\"source\":\"祖父\",\"target\":\"お爺様\"},{\"weight\":0.65,\"source\":\"祖父\",\"target\":\"お爺\"}],\"center\":{\"id\":\"祖父\"}}"
}
```
- Code
```js
await page.evaluate('() => fetch(\'http://localhost:8000/api/v1/lexical/graph?center=%E7%A5%96%E7%88%B6&depth=1&searchField=translation\').then(async r => ({ status: r.status, text: await r.text() }))');
```
- Snapshot: 056.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e421",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('nextjs-portal > div > div').first().click();
```
- Snapshot: 057.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e421",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('nextjs-portal > div > div').first().click();
```
- Snapshot: 058.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e421",
  "button": "left",
  "modifiers": 0,
  "clickCount": 2
}
```
- Code
```js
await page.locator('nextjs-portal > div > div').first().dblclick();
```
- Snapshot: 059.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e1",
  "key": "F5",
  "modifiers": 2
}
```
- Code
```js
await page.getByText('Skip to contentAI Language').press('ControlOrMeta+F5');
```
- Snapshot: 060.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 373,
    "y": 296
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 373,
      y: 296
    }
  });
```
- Snapshot: 061.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 281,
    "y": 324
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 281,
      y: 324
    }
  });
```
- Snapshot: 062.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 186,
    "y": 388
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 186,
      y: 388
    }
  });
```
- Snapshot: 063.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 271,
    "y": 175
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 271,
      y: 175
    }
  });
```
- Snapshot: 064.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 228,
    "y": 262
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 228,
      y: 262
    }
  });
```
- Snapshot: 065.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 333,
    "y": 103
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 333,
      y: 103
    }
  });
```
- Snapshot: 066.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 418,
    "y": 109
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 418,
      y: 109
    }
  });
```
- Snapshot: 067.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 519,
    "y": 231
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 519,
      y: 231
    }
  });
```
- Snapshot: 068.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 482,
    "y": 287
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 482,
      y: 287
    }
  });
```
- Snapshot: 069.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 490,
    "y": 246
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 490,
      y: 246
    }
  });
```
- Snapshot: 070.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e44",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Info' }).click();
```
- Snapshot: 071.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e488",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Generate AI Content' }).click();
```
- Snapshot: 072.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e45",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Lesson' }).click();
```
- Snapshot: 073.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e45",
  "key": "ArrowUp",
  "modifiers": 0
}
```
- Code
```js
await page.getByRole('button', { name: 'Lesson' }).press('ArrowUp');
```
- Snapshot: 074.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e45",
  "key": "ArrowUp",
  "modifiers": 0
}
```
- Code
```js
await page.getByRole('button', { name: 'Lesson' }).press('ArrowUp');
```
- Snapshot: 075.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e45",
  "key": "ArrowDown",
  "modifiers": 0
}
```
- Code
```js
await page.getByRole('button', { name: 'Lesson' }).press('ArrowDown');
```
- Snapshot: 076.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e42",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Graph' }).click();
```
- Snapshot: 077.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e620",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Fit' }).click();
```
- Snapshot: 078.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e624",
  "position": {
    "x": 396,
    "y": 96
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 396,
      y: 96
    }
  });
```
- Snapshot: 079.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 080.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 081.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "blood"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('blood');
```
- Snapshot: 082.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e624",
  "position": {
    "x": 490,
    "y": 307
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 490,
      y: 307
    }
  });
```
- Snapshot: 083.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e624",
  "position": {
    "x": 412,
    "y": 107
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 412,
      y: 107
    }
  });
```
- Snapshot: 084.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e905",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Fit' }).click();
```
- Snapshot: 085.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e38",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: '⚙️ Settings' }).click();
```
- Snapshot: 086.snapshot.yml


### User action: check
- Args
```json
{
  "name": "check",
  "ref": "e984"
}
```
- Code
```js
await page.getByRole('checkbox', { name: 'Exact Match' }).check();
```
- Snapshot: 087.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 088.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 089.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "blood"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('blood');
```
- Snapshot: 090.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e624",
  "position": {
    "x": 318,
    "y": 339
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 318,
      y: 339
    }
  });
```
- Snapshot: 091.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 092.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "b"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('b');
```
- Snapshot: 093.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "bloo"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('bloo');
```
- Snapshot: 094.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "blood"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('blood');
```
- Snapshot: 095.snapshot.yml


### Tool call: browser_evaluate
- Args
```json
{
  "function": "() => fetch('http://localhost:8000/api/v1/lexical/graph?center=blood&depth=1&searchField=translation').then(async r => ({ status: r.status, json: await r.json() }))"
}
```
- Result
```
{
  "status": 200,
  "json": {
    "nodes": [
      {
        "kanji": "血",
        "hiragana": "ち",
        "translation": "blood",
        "level": null,
        "domain": null,
        "pos": null,
        "id": "血"
      },
      {
        "id": "赤血球",
        "level": null,
        "hiragana": "せっけっきゅう",
        "translation": "red blood cell",
        "name": "赤血球",
        "domain": null,
        "pos": null
      },
      {
        "id": "血管炎",
        "level": null,
        "hiragana": "けっかんえん",
        "translation": "vasculitis",
        "name": "血管炎",
        "domain": null,
        "pos": null
      },
      {
        "id": "血友病",
        "level": null,
        "hiragana": "けつゆうびょう",
        "translation": "hemophilia",
        "name": "血友病",
        "domain": null,
        "pos": null
      },
      {
        "id": "血管",
        "level": null,
        "hiragana": "けっかん",
        "translation": "blood vessel",
        "name": "血管",
        "domain": null,
        "pos": null
      },
      {
        "id": "血圧",
        "level": null,
        "hiragana": "けつあつ",
        "translation": "blood pressure",
        "name": "血圧",
        "domain": null,
        "pos": null
      },
      {
        "id": "血液",
        "level": null,
        "hiragana": "けつえき",
        "translation": "blood",
        "name": "血液",
        "domain": null,
        "pos": null
      },
      {
        "id": "血尿",
        "level": null,
        "hiragana": "けつにょう",
        "translation": "hematuria",
        "name": "血尿",
        "domain": null,
        "pos": null
      },
      {
        "id": "血栓",
        "level": null,
        "hiragana": "けっせん",
        "translation": "thrombus",
        "name": "血栓",
        "domain": null,
        "pos": null
      },
      {
        "id": "血潮",
        "level": null,
        "hiragana": "ちしお",
        "translation": "blood tide",
        "name": "血潮",
        "domain": null,
        "pos": null
      },
      {
        "id": "血痕",
        "level": null,
        "hiragana": "けっこん",
        "translation": "bloodstain",
        "name": "血痕",
        "domain": null,
        "pos": null
      },
      {
        "id": "血糖",
        "level": null,
        "hiragana": "けっとう",
        "translation": "blood sugar",
        "name": "血糖",
        "domain": null,
        "pos": null
      },
      {
        "id": "血清",
        "level": null,
        "hiragana": "けっせい",
        "translation": "serum",
        "name": "血清",
        "domain": null,
        "pos": null
      },
      {
        "id": "血統",
        "level": null,
        "hiragana": "けっとう",
        "translation": "lineage",
        "name": "血統",
        "domain": null,
        "pos": null
      },
      {
        "id": "血縁",
        "level": null,
        "hiragana": "けつえん",
        "translation": "blood relation",
        "name": "血縁",
        "domain": null,
        "pos": null
      }
    ],
    "links": [
      {
        "weight": 0.8,
        "source": "血",
        "target": "赤血球"
      },
      {
        "weight": 0.8,
        "source": "赤血球",
        "target": "血"
      },
      {
        "weight": 0.25,
        "source": "血管炎",
        "target": "血"
      },
      {
        "weight": 0.4,
        "source": "血友病",
        "target": "血"
      },
      {
        "weight": 0.7,
        "source": "血管",
        "target": "血"
      },
      {
        "weight": 0.35,
        "source": "血圧",
        "target": "血"
      },
      {
        "weight": 0.95,
        "source": "血液",
        "target": "血"
      },
      {
        "weight": 0.45,
        "source": "血尿",
        "target": "血"
      },
      {
        "weight": 0.2,
        "source": "血栓",
        "target": "血"
      },
      {
        "weight": 0.75,
        "source": "血潮",
        "target": "血"
      },
      {
        "weight": 0.5,
        "source": "血痕",
        "target": "血"
      },
      {
        "weight": 0.3,
        "source": "血糖",
        "target": "血"
      },
      {
        "weight": 0.55,
        "source": "血清",
        "target": "血"
      },
      {
        "weight": 0.65,
        "source": "血統",
        "target": "血"
      },
      {
        "weight": 0.6,
        "source": "血縁",
        "target": "血"
      },
      {
        "weight": 0.35,
        "source": "血",
        "target": "血圧"
      },
      {
        "weight": 0.95,
        "source": "血",
        "target": "血液"
      },
      {
        "weight": 0.7,
        "source": "血管",
        "target": "血液"
      },
      {
        "weight": 0.7,
        "source": "血尿",
        "target": "血液"
      },
      {
        "weight": 0.85,
        "source": "血潮",
        "target": "血液"
      },
      {
        "weight": 0.75,
        "source": "血痕",
        "target": "血液"
      },
      {
        "weight": 0.85,
        "source": "血清",
        "target": "血液"
      },
      {
        "weight": 0.68,
        "source": "血統",
        "target": "血縁"
      },
      {
        "weight": 0.6,
        "source": "血",
        "target": "血縁"
      },
      {
        "weight": 0.7,
        "source": "血",
        "target": "血管"
      },
      {
        "weight": 0.45,
        "source": "血管炎",
        "target": "血管"
      },
      {
        "weight": 0.7,
        "source": "血液",
        "target": "血管"
      },
      {
        "weight": 0.65,
        "source": "血",
        "target": "血統"
      },
      {
        "weight": 0.68,
        "source": "血縁",
        "target": "血統"
      },
      {
        "weight": 0.55,
        "source": "血",
        "target": "血清"
      },
      {
        "weight": 0.85,
        "source": "血液",
        "target": "血清"
      },
      {
        "weight": 0.3,
        "source": "血",
        "target": "血糖"
      },
      {
        "weight": 0.5,
        "source": "血",
        "target": "血痕"
      },
      {
        "weight": 0.75,
        "source": "血液",
        "target": "血痕"
      },
      {
        "weight": 0.85,
        "source": "血液",
        "target": "血潮"
      },
      {
        "weight": 0.75,
        "source": "血",
        "target": "血潮"
      },
      {
        "weight": 0.2,
        "source": "血",
        "target": "血栓"
      },
      {
        "weight": 0.7,
        "source": "血液",
        "target": "血尿"
      },
      {
        "weight": 0.45,
        "source": "血",
        "target": "血尿"
      },
      {
        "weight": 0.25,
        "source": "血",
        "target": "血管炎"
      },
      {
        "weight": 0.45,
        "source": "血管",
        "target": "血管炎"
      },
      {
        "weight": 0.4,
        "source": "血",
        "target": "血友病"
      }
    ],
    "center": {
      "id": "血"
    }
  }
}
```
- Code
```js
await page.evaluate('() => fetch(\'http://localhost:8000/api/v1/lexical/graph?center=blood&depth=1&searchField=translation\').then(async r => ({ status: r.status, json: await r.json() }))');
```
- Snapshot: 096.snapshot.yml


### User action: navigate
- Args
```json
{
  "name": "navigate",
  "url": "http://localhost:3000/lexical/graph"
}
```
- Code
```js
await page.goto('http://localhost:3000/lexical/graph');
```
- Snapshot: 097.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 098.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 099.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "blood"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('blood');
```
- Snapshot: 100.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e120",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Fit' }).click();
```
- Snapshot: 101.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 102.snapshot.yml


### User action: press
- Args
```json
{
  "name": "press",
  "ref": "e30",
  "key": "ArrowLeft",
  "modifiers": 10
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).press('ControlOrMeta+Shift+ArrowLeft');
```
- Snapshot: 103.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "moh"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('moh');
```
- Snapshot: 104.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mothe"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mothe');
```
- Snapshot: 105.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "mother"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('mother');
```
- Snapshot: 106.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e63",
  "position": {
    "x": 368,
    "y": 326
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 368,
      y: 326
    }
  });
```
- Snapshot: 107.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e255",
  "button": "left",
  "modifiers": 0,
  "clickCount": 2
}
```
- Code
```js
await page.locator('div').filter({ hasText: 'Loading new graph...' }).nth(5).dblclick();
```
- Snapshot: 108.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e338",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: '3D' }).click();
```
- Snapshot: 109.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e358",
  "position": {
    "x": 378,
    "y": 376
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 378,
      y: 376
    }
  });
```
- Snapshot: 110.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e358",
  "position": {
    "x": 658,
    "y": 367
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 658,
      y: 367
    }
  });
```
- Snapshot: 111.snapshot.yml


### User action: select
- Args
```json
{
  "name": "select",
  "ref": "e349",
  "options": [
    "2"
  ]
}
```
- Code
```js
await page.getByRole('combobox').selectOption('2');
```
- Snapshot: 112.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e358",
  "position": {
    "x": 658,
    "y": 358
  },
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('canvas').click({
    position: {
      x: 658,
      y: 358
    }
  });
```
- Snapshot: 113.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e351",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: '2D' }).click();
```
- Snapshot: 114.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e30",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).click();
```
- Snapshot: 115.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": ""
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('');
```
- Snapshot: 116.snapshot.yml


### User action: fill
- Args
```json
{
  "name": "fill",
  "ref": "e30",
  "text": "home"
}
```
- Code
```js
await page.getByRole('textbox', { name: 'Enter kanji/hiragana/' }).fill('home');
```
- Snapshot: 117.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e44",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Info' }).click();
```
- Snapshot: 118.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e24",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('#main-content').click();
```
- Snapshot: 119.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e42",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Graph' }).click();
```
- Snapshot: 120.snapshot.yml


### User action: select
- Args
```json
{
  "name": "select",
  "ref": "e815",
  "options": [
    "1"
  ]
}
```
- Code
```js
await page.getByRole('combobox').selectOption('1');
```
- Snapshot: 121.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e1007",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Fit' }).click();
```
- Snapshot: 122.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e14",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Grammar' }).click();
```
- Snapshot: 123.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e1013",
  "button": "right",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('link', { name: 'Grammar Study Grammar' }).click({
    button: 'right'
  });
```
- Snapshot: 124.snapshot.yml


### User action: openPage
- Args
```json
{
  "name": "openPage",
  "url": "http://localhost:3000/grammar"
}
```
- Snapshot: 125.snapshot.yml


### User action: navigate
- Args
```json
{
  "name": "navigate",
  "url": "http://localhost:3000/grammar"
}
```
- Code
```js
await page2.goto('http://localhost:3000/grammar');
```
- Snapshot: 126.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e81",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page2.getByRole('button', { name: 'Study This Pattern' }).first().click();
```
- Snapshot: 127.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e24",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('#main-content').click();
```
- Snapshot: 128.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e24",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('#main-content').click();
```
- Snapshot: 129.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e26",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByText('Lexical GraphSearching in:').click();
```
- Snapshot: 130.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e26",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByText('Lexical GraphSearching in:').click();
```
- Snapshot: 131.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e1020",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('.fixed').click();
```
- Snapshot: 132.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e20",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByRole('button', { name: 'Profile' }).click();
```
- Snapshot: 133.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e26",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByText('Lexical GraphSearching in:').click();
```
- Snapshot: 134.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e26",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByText('Lexical GraphSearching in:').click();
```
- Snapshot: 135.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e1032",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.locator('.fixed').click();
```
- Snapshot: 136.snapshot.yml


### User action: click
- Args
```json
{
  "name": "click",
  "ref": "e25",
  "button": "left",
  "modifiers": 0,
  "clickCount": 1
}
```
- Code
```js
await page.getByText('Lexical GraphSearching in: kanjiKHTSearch⚙️ SettingsGraphInfoLessonSelected').click();
```
- Snapshot: 137.snapshot.yml

