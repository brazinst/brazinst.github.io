import fs from 'fs';
import path from 'path';
import assert from 'assert';

const requiredFiles = [
  { file: 'src/components/FamilyTabs.astro', tokens: ['activeFamily', 'counts', 'aerofones', 'cordofones', 'idiofones', 'membranofones'] },
  { file: 'src/components/InstrumentCard.astro', tokens: ['instrument', 'data', 'familyColors', 'mimo_code', 'coverImg'] },
  { file: 'src/pages/index.astro', tokens: ['getCollection', 'Hero', 'FamilyTabs', 'InstrumentCard', 'counts'] },
  { file: 'src/pages/familia/[family].astro', tokens: ['getStaticPaths', 'getCollection', 'FamilyTabs', 'InstrumentCard', 'counts', 'familyNames'] },
];

requiredFiles.forEach(({ file, tokens }) => {
  const p = path.resolve(file);
  assert.ok(fs.existsSync(p), `Arquivo ${file} deve existir`);
  const content = fs.readFileSync(p, 'utf-8');
  assert.ok(content.length > 50, `Arquivo ${file} deve ter conteúdo substancial`);
  tokens.forEach(tok => {
    assert.ok(content.includes(tok), `Arquivo ${file} deve conter o termo '${tok}'`);
  });
});

console.log('✅ Teste de cards, grade e filtros de família aprovado!');
