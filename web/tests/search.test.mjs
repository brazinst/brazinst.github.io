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

// Teste funcional em runtime do Pagefind (se os arquivos compilados existirem em dist/)
const pagefindEntry = path.resolve('dist/pagefind/pagefind.js');
if (fs.existsSync(pagefindEntry)) {
  globalThis.fetch = async (url) => {
    let uStr = url.toString();
    if (uStr.includes('?')) uStr = uStr.split('?')[0];
    let targetPath;
    if (uStr.startsWith('file://')) {
      targetPath = uStr.replace('file://', '');
    } else if (uStr.startsWith('/')) {
      targetPath = path.resolve('dist', uStr.slice(1));
    } else {
      targetPath = uStr;
    }
    const buf = fs.readFileSync(targetPath);
    return {
      ok: true,
      status: 200,
      arrayBuffer: async () => buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength),
      json: async () => JSON.parse(buf.toString('utf-8')),
      text: async () => buf.toString('utf-8'),
    };
  };

  const pagefind = await import(pagefindEntry);
  await pagefind.init();

  const testQueries = ['berimbau', 'capoeira', 'maracatu', 'guarara', 'enxada', 'upawa'];
  for (const q of testQueries) {
    const searchRes = await pagefind.search(q);
    assert.ok(searchRes.results.length > 0, `Busca Pagefind por '${q}' deve retornar resultados no acervo`);
  }
  console.log(`✅ Teste funcional de busca Pagefind aprovado: consultas retornaram verbetes reais!`);
}

console.log('✅ Teste de busca Pagefind e página institucional Sobre aprovado!');
