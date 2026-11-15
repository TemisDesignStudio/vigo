import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import test from 'node:test';

const output = new URL('../out/', import.meta.url);

test('static export includes the Vigo page and public images', async () => {
  const page = await readFile(new URL('index.html', output), 'utf8');

  assert.match(page, /VIGO/);
  await access(new URL('images/hero-man.png', output));
  await access(new URL('images/hero-woman-navy.png', output));
  await access(new URL('images/hero-woman-peach.png', output));
});
