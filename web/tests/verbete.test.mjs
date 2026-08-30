import fs from 'fs';
import path from 'path';
import assert from 'assert';

const requiredFiles = [
  {
    file: 'src/components/MediaGallery.astro',
    tokens: ['images', 'caption', 'rights', 'Registros Iconográficos', 'instrumentTitle'],
  },
  {
    file: 'src/components/AudioPlayer.astro',
    tokens: ['links', 'getYouTubeId', 'youtube-nocookie.com/embed', 'Fonografia e Registros Sonoros'],
  },
  {
    file: 'src/components/CitationBox.astro',
    tokens: ['Como citar este verbete', 'copy-citation-btn', 'navigator.clipboard', 'ABNT', 'Brazil Instrumentarium'],
  },
  {
    file: 'src/pages/instrumentos/[slug].astro',
    tokens: ['getStaticPaths', 'getCollection', 'MediaGallery', 'AudioPlayer', 'CitationBox', 'data-pagefind-body'],
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

console.log('✅ Teste de verbetes individuais, galeria, áudio e citação aprovado!');
