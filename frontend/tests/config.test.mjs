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
