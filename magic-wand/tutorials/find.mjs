#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { findGuides } from '../../docs/how-to/gallery.mjs';
const index = JSON.parse(readFileSync(new URL('../../docs/how-to/tutorials.json', import.meta.url), 'utf8'));
console.log(JSON.stringify(findGuides(index.guides, process.argv.slice(2).join(' ')), null, 2));
