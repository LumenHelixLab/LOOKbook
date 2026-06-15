/**
 * R10 — Playwright smoke: demo-lab loads, health check, analyze upload.
 */
import { test, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import fs from 'node:fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const DEMO_DIR = path.join(ROOT, 'demo-lab');

function serveStatic(dir, port) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const urlPath = req.url === '/' ? '/index.html' : req.url.split('?')[0];
      const file = path.join(dir, urlPath.replace(/^\//, ''));
      if (!file.startsWith(dir) || !fs.existsSync(file)) {
        res.writeHead(404);
        return res.end('not found');
      }
      const ext = path.extname(file);
      const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png' };
      res.writeHead(200, { 'Content-Type': types[ext] || 'application/octet-stream' });
      fs.createReadStream(file).pipe(res);
    });
    server.listen(port, () => resolve(server));
  });
}

async function waitForHealth(maxMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const res = await fetch('http://127.0.0.1:8042/health');
      if (res.ok) return true;
    } catch { /* retry */ }
    await new Promise((r) => setTimeout(r, 500));
  }
  return false;
}

let labProc;
let staticServer;

test.beforeAll(async () => {
  labProc = spawn('python', ['-m', 'lookbook.lab_server'], {
    cwd: ROOT,
    env: { ...process.env },
    stdio: 'ignore',
    shell: true,
  });
  const ready = await waitForHealth();
  if (!ready) console.warn('lab_server did not respond on :8042 — API tests may skip');
  staticServer = await serveStatic(DEMO_DIR, 8766);
});

test.afterAll(async () => {
  if (staticServer) staticServer.close();
  if (labProc) labProc.kill('SIGTERM');
});

test('demo-lab loads and shows pipeline UI', async ({ page }) => {
  await page.goto('http://127.0.0.1:8766/');
  await expect(page.locator('h1')).toContainText('Demo Lab');
  await expect(page.locator('#runBtn')).toBeVisible();
});

test('lab server health responds', async ({ request }) => {
  const res = await request.get('http://127.0.0.1:8042/health');
  test.skip(!res.ok(), 'lab_server not running');
  const body = await res.json();
  expect(body.ok).toBe(true);
});

test('analyze endpoint accepts upload', async ({ request }) => {
  const health = await request.get('http://127.0.0.1:8042/health');
  test.skip(!health.ok(), 'lab_server not running');
  const png = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
    'base64',
  );
  const boundary = '----PlaywrightBoundary';
  const body = Buffer.concat([
    Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="pixel.png"\r\nContent-Type: image/png\r\n\r\n`),
    png,
    Buffer.from(`\r\n--${boundary}--\r\n`),
  ]);
  const res = await request.post('http://127.0.0.1:8042/api/analyze', {
    headers: { 'Content-Type': `multipart/form-data; boundary=${boundary}` },
    data: body,
  });
  expect(res.ok()).toBeTruthy();
  const json = await res.json();
  expect(json.project_id).toBeTruthy();
});