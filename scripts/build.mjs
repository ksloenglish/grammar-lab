import { cpSync, rmSync } from 'node:fs';
import './validate.mjs';
rmSync(new URL('../dist/', import.meta.url), { recursive: true, force: true });
cpSync(new URL('../site/', import.meta.url), new URL('../dist/', import.meta.url), { recursive: true });
console.log('Static app packaged in dist/. No runtime dependencies or backend.');
