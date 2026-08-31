import fs from 'fs';
import path from 'path';
import assert from 'assert';

const contentDir = path.resolve('src/content/instruments');
const families = ['aerofones', 'cordofones', 'idiofones', 'membranofones'];

let total = 0;
let nonEmptyBodies = 0;

families.forEach(fam => {
  const p = path.join(contentDir, fam);
  assert.ok(fs.existsSync(p), `Pasta da família ${fam} deve existir`);
  const files = fs.readdirSync(p).filter(f => f.endsWith('.md'));
  assert.ok(files.length > 0, `Família ${fam} deve conter instrumentos`);
  total += files.length;

  files.forEach(f => {
    const raw = fs.readFileSync(path.join(p, f), 'utf-8');
    const parts = raw.split('---');
    assert.ok(parts.length >= 3, `Arquivo ${f} deve ter frontmatter YAML válido`);
    const body = parts.slice(2).join('---').trim();
    assert.ok(body.length > 20, `Arquivo ${f} deve ter corpo de texto não-vazio`);
    nonEmptyBodies++;
  });
});

assert.strictEqual(total, 165, `Total de instrumentos deve ser exatamente 165 (encontrados: ${total})`);
assert.strictEqual(nonEmptyBodies, 165, `Todos os 165 instrumentos devem possuir corpo de texto não-vazio`);
console.log(`✅ Teste de conteúdo aprovado: 165/165 instrumentos validados com textos integrais em src/content/instruments/!`);
