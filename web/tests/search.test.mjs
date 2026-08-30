import fs from 'fs';
import path from 'path';
import assert from 'assert';

const requiredFiles = [
  {
    file: 'src/components/SearchModal.astro',
    tokens: [
      'search-modal',
      'search-input',
      'search-results',
      'search-close',
      '/pagefind/pagefind.js',
      'pagefind.search',
      'initPagefind',
      'Escape'
    ],
  },
  {
    file: 'src/pages/sobre.astro',
    tokens: [
      'BaseLayout',
      'Sobre o Brazil Instrumentarium',
      'LABEET',
      'Alice Satomi',
      'MIMO',
      'Aerofones',
      'Cordofones',
      'Idiofones',
      'Membranofones',
      'Preservação Digital'
    ],
  },
  {
    file: 'src/layouts/BaseLayout.astro',
    tokens: [
      'SearchModal',
      '<SearchModal'
    ],
  },
];

requiredFiles.forEach(({ file, tokens }) => {
  const p = path.resolve(file);
  assert.ok(fs.existsSync(p), `Arquivo ${file} deve existir`);
  const content = fs.readFileSync(p, 'utf-8');
  assert.ok(content.length > 50, `Arquivo ${file} deve ter conteúdo substancial`);
  tokens.forEach((tok) => {
    assert.ok(content.includes(tok), `Arquivo ${file} deve conter o termo '${tok}'`);
  });
});

console.log('✅ Teste de busca Pagefind e página institucional Sobre aprovado!');
