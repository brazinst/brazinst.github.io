import fs from 'fs';
import path from 'path';
import assert from 'assert';

const contentDir = path.resolve('src/content/instruments');
const families = ['aerofones', 'cordofones', 'idiofones', 'membranofones'];

let total = 0;
families.forEach(fam => {
  const p = path.join(contentDir, fam);
  assert.ok(fs.existsSync(p), `Pasta da família ${fam} deve existir`);
  const files = fs.readdirSync(p).filter(f => f.endsWith('.md'));
  assert.ok(files.length > 0, `Família ${fam} deve conter instrumentos`);
  total += files.length;
});

assert.strictEqual(total, 78, 'Total de instrumentos deve ser exatamente 78');
console.log(`✅ Teste de conteúdo aprovado: 78/78 instrumentos validados em src/content/instruments/!`);
