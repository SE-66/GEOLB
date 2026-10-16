const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
fs.rmSync(dist, { recursive: true, force: true });
fs.mkdirSync(dist, { recursive: true });
for (const name of ['index.html','address.html','verify.html','studio.html','deployment-check.json']) {
  const source = path.join(root, name);
  if (!fs.existsSync(source)) throw new Error('Missing required static asset: ' + name);
  fs.copyFileSync(source, path.join(dist, name));
}
fs.cpSync(path.join(root, 'data'), path.join(dist, 'data'), {recursive: true});
console.log('GeoLB static assets built into dist/');
