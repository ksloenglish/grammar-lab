import { cpSync, rmSync, readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { VERSION } from '../site/version.js';
import './validate.mjs';

if (!/^v\d{6}-\d{6}$/.test(VERSION)) throw new Error('Invalid deployment version');
const output = new URL('../dist/', import.meta.url);
rmSync(output, { recursive: true, force: true });
cpSync(new URL('../site/', import.meta.url), output, { recursive: true });

// Version every browser module edge, not just the entry file: old cached dependencies
// must never interpret newer question banks or spelling operations.
for (const name of readdirSync(new URL('js/', output))) {
  if (!name.endsWith('.js')) continue;
  const file = new URL(`js/${name}`, output);
  const source = readFileSync(file, 'utf8').replace(/(from\s+)(['"])(\.{1,2}\/[^'"]+\.js)\2/g,
    (_, prefix, quote, path) => `${prefix}${quote}${path}?v=${VERSION}${quote}`);
  writeFileSync(file, source);
}
const entry = new URL('index.html', output);
writeFileSync(entry, readFileSync(entry, 'utf8').replace(/((?:href|src)=['"])(\.\/[^'"]+\.(?:css|js))(['"])/g,
  (_, start, path, end) => `${start}${path}?v=${VERSION}${end}`));
console.log(`Static app packaged in dist/ with ${VERSION} asset URLs. No runtime dependencies or backend.`);
