// Apply the same physical stock and entry ends to an offline CAD guide as to a browser view.
import { readFileSync } from 'node:fs';
import { withStockRods } from './stock-rod.mjs';

const guide = JSON.parse(readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(withStockRods(guide, process.argv[2])));
