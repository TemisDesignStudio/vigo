import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

test('static export is enabled', async () => {
  const config = await readFile(new URL('../next.config.mjs', import.meta.url), 'utf8');

  assert.match(config, /output:\s*['"]export['"]/);
});

test('each budget has a complete fixed campaign option', async () => {
  const page = await readFile(new URL('../app/page.jsx', import.meta.url), 'utf8');

  for (const amount of ['۵ میلیون تومان', '۱۰ میلیون تومان', '۲۵ میلیون تومان']) {
    assert.match(page, new RegExp(`'${amount}'`));
  }
  assert.match(page, /useState\('۵ میلیون تومان'\)/);
  assert.match(page, /campaign\.collaborators/);
  assert.match(page, /campaign\.reels/);
  assert.match(page, /campaign\.views/);
  assert.match(page, /campaign\.summary/);
  assert.match(page, /campaign\.details/);
});

test('login page and header link use the expected UI contract', async () => {
  const [login, styles, page] = await Promise.all([
    readFile(new URL('../app/login/page.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../app/login/login.module.css', import.meta.url), 'utf8'),
    readFile(new URL('../app/page.jsx', import.meta.url), 'utf8'),
  ]);

  assert.match(page, /href="\/login\/"/);
  assert.match(login, /dir="ltr"/);
  assert.match(styles, /height: 50px/);
  assert.match(styles, /border-radius: 12px/);
  assert.match(styles, /\.field input:focus/);
});

test('public forms and the admin panel use the Vigo API contract', async () => {
  const [forms, admin] = await Promise.all([
    readFile(new URL('../app/requests/RequestForms.jsx', import.meta.url), 'utf8'),
    readFile(new URL('../app/admin/page.jsx', import.meta.url), 'utf8'),
  ]);

  assert.match(forms, /'\/api\/campaigns'/);
  assert.match(forms, /'\/api\/collaboration-requests'/);
  assert.match(admin, /'\/api\/admin\/campaigns'/);
  assert.match(admin, /'\/api\/admin\/collaboration-requests'/);
  assert.match(admin, /\/status/);
});
