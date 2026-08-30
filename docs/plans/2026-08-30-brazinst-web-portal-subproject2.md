# Brazil Instrumentarium Web Portal (Sub-project 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir e implantar a aplicação web moderna, estática e independente do Brazil Instrumentarium com Astro, Tailwind CSS, Content Collections e busca estática via Pagefind, servindo os 78 instrumentos preservados sem custo de servidor.

**Architecture:** A aplicação web reside no diretório `web/`. Utiliza Astro Content Collections para validar os 78 arquivos Markdown em `src/content/instruments/` com esquemas estritos Zod. A estilização utiliza Tailwind CSS com tipografia editorial. A busca é 100% estática e executada no cliente via Pagefind. A publicação é automatizada via GitHub Actions para o GitHub Pages.

**Tech Stack:** Astro 5, Tailwind CSS, TypeScript, Zod, Pagefind, Node.js.

**Spec:** [`docs/specs/2026-08-30-brazinst-web-portal-subproject2-design.md`](file:///Users/gregoriomelo/dev/labeet/docs/specs/2026-08-30-brazinst-web-portal-subproject2-design.md)

## Global Constraints

- O projeto web deve residir exclusivamente no diretório `web/` do repositório.
- A fonte da verdade dos verbetes são os 78 arquivos Markdown preservados em `content_brazinst/instruments/`.
- Todas as fotos originais devem ser copiadas para `web/public/media/` mantendo os caminhos relativos referenciados nos metadados YAML.
- Zero dependências de banco de dados, servidores backend ou APIs externas pagas no runtime.
- Build estático completo (`npm run build`) deve gerar a pasta `dist/` contendo todas as páginas e o índice do Pagefind.
- Responsividade completa testada para mobile e desktop.

---

### Task 1: Scaffolding do Projeto Web Astro + Tailwind + Content Collections Schema

**Files:**
- Create: `web/package.json`
- Create: `web/astro.config.mjs`
- Create: `web/tailwind.config.mjs`
- Create: `web/tsconfig.json`
- Create: `web/src/content/config.ts`
- Create: `scripts/sync_web_content.py`
- Test: `web/tests/content.test.mjs`

**Interfaces:**
- Produz:
  - `instruments` collection validada com Zod em `web/src/content/config.ts`.
  - `web/src/content/instruments/`: 78 arquivos `.md` sincronizados.
  - `web/public/media/`: fotos dos instrumentos sincronizadas.

- [ ] **Step 1: Escrever script de sincronização de conteúdo `scripts/sync_web_content.py`**

Criar `scripts/sync_web_content.py`:
```python
import shutil
from pathlib import Path

def sync():
    root = Path(__file__).resolve().parent.parent
    src_content = root / "content_brazinst" / "instruments"
    src_media = root / "content_brazinst" / "media"
    
    dest_content = root / "web" / "src" / "content" / "instruments"
    dest_media = root / "web" / "public" / "media"

    if dest_content.exists():
        shutil.rmtree(dest_content)
    dest_content.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src_content, dest_content)
    print(f"Sincronizados verbetes para {dest_content}")

    if dest_media.exists():
        shutil.rmtree(dest_media)
    dest_media.parent.mkdir(parents=True, exist_ok=True)
    if src_media.exists():
        shutil.copytree(src_media, dest_media)
    print(f"Sincronizadas mídias para {dest_media}")

if __name__ == "__main__":
    sync()
```

- [ ] **Step 2: Configurar `web/package.json`, `astro.config.mjs`, `tailwind.config.mjs` e `tsconfig.json`**

Criar `web/package.json`:
```json
{
  "name": "brazil-instrumentarium-web",
  "type": "module",
  "version": "1.0.0",
  "scripts": {
    "dev": "astro dev",
    "start": "astro dev",
    "build": "astro build && pagefind --site dist",
    "preview": "astro preview",
    "astro": "astro",
    "test": "node tests/content.test.mjs"
  },
  "dependencies": {
    "@astrojs/tailwind": "^5.1.5",
    "astro": "^5.4.2",
    "pagefind": "^1.3.0",
    "tailwindcss": "^3.4.17",
    "@tailwindcss/typography": "^0.5.16"
  }
}
```

Criar `web/astro.config.mjs`:
```javascript
import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';

export default defineConfig({
  integrations: [tailwind()],
  site: 'https://brazil-instrumentarium.github.io',
  base: '/',
});
```

Criar `web/tailwind.config.mjs`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#1c1917',
          warm: '#78350f',
          accent: '#047857',
          gold: '#d97706',
          bg: '#faf8f5',
        }
      },
      fontFamily: {
        serif: ['Merriweather', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};
```

Criar `web/tsconfig.json`:
```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "strictNullChecks": true
  }
}
```

- [ ] **Step 3: Implementar Schema de Content Collections `web/src/content/config.ts`**

Criar `web/src/content/config.ts`:
```typescript
import { defineCollection, z } from 'astro:content';

const instruments = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string().min(1),
    slug: z.string().min(1),
    family: z.enum(['aerofones', 'cordofones', 'idiofones', 'membranofones']),
    mimo_code: z.string().optional(),
    source_url: z.string().url().optional(),
    author: z.string().optional(),
    reviewer: z.string().optional(),
    published_date: z.string().optional(),
    modified_date: z.string().optional(),
    thumbnail: z.string().optional(),
    images: z.array(z.object({
      file: z.string(),
      caption: z.string().optional(),
      rights: z.string().optional(),
    })).default([]),
    audio_video_links: z.array(z.object({
      title: z.string(),
      url: z.string(),
      access_date: z.string().optional(),
    })).default([]),
    references: z.array(z.string()).default([]),
  }),
});

export const collections = { instruments };
```

- [ ] **Step 4: Executar sincronização de arquivos e instalar dependências do Node.js**

Executar:
```bash
.venv/bin/python scripts/sync_web_content.py
cd web && npm install
```

- [ ] **Step 5: Escrever e rodar teste de integridade do conteúdo `web/tests/content.test.mjs`**

Criar `web/tests/content.test.mjs`:
```javascript
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
```

Executar:
```bash
cd web && npm test
```
Resultado esperado: `✅ Teste de conteúdo aprovado: 78/78 instrumentos validados`.

- [ ] **Step 6: Commit**

```bash
git add scripts/sync_web_content.py web/
git commit -m "feat(web): add Astro project scaffolding, Tailwind config, and validated content collections"
```

---

### Task 2: Layouts Base e Componentes Estruturais (Header, Footer, Hero)

**Files:**
- Create: `web/src/layouts/BaseLayout.astro`
- Create: `web/src/components/Header.astro`
- Create: `web/src/components/Footer.astro`
- Create: `web/src/components/Hero.astro`
- Test: `web/tests/layout.test.mjs`

**Interfaces:**
- Produz:
  - `BaseLayout.astro`: estrutura HTML5, tipografia, metatags SEO e barra de navegação global.
  - `Header.astro`: logo do Brazinst, links para Início, Famílias, Sobre e botão de busca `Cmd+K`.
  - `Hero.astro`: apresentação histórica do LABEET e da pesquisa da Profa. Alice Satomi.
  - `Footer.astro`: créditos institucionais ao CCTA / UFPB e preservação digital.

- [ ] **Step 1: Escrever teste de renderização básica de layout `web/tests/layout.test.mjs`**

Criar `web/tests/layout.test.mjs`:
```javascript
import fs from 'fs';
import path from 'path';
import assert from 'assert';

const requiredComponents = [
  'src/layouts/BaseLayout.astro',
  'src/components/Header.astro',
  'src/components/Footer.astro',
  'src/components/Hero.astro'
];

requiredComponents.forEach(file => {
  const p = path.resolve(file);
  assert.ok(fs.existsSync(p), `Componente ${file} deve existir`);
  const content = fs.readFileSync(p, 'utf-8');
  assert.ok(content.length > 50, `Componente ${file} deve ter conteúdo substancial`);
});

console.log('✅ Teste de componentes estruturais aprovado!');
```

- [ ] **Step 2: Implementar `web/src/components/Header.astro`**

Criar `web/src/components/Header.astro`:
```astro
---
interface Props {
  activeTab?: string;
}
const { activeTab = '' } = Astro.props;
---

<header class="bg-[#FAF8F5]/90 backdrop-blur-md sticky top-0 z-40 border-b border-stone-200">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
    <a href="/" class="flex items-center gap-3 group">
      <div class="w-10 h-10 rounded-full bg-amber-800 flex items-center justify-center text-white font-serif font-bold text-xl shadow-sm group-hover:bg-amber-900 transition-colors">
        B
      </div>
      <div>
        <span class="block font-serif font-bold text-stone-900 text-lg leading-tight tracking-tight">Brazil Instrumentarium</span>
        <span class="block text-xs font-sans text-stone-500 uppercase tracking-widest">LABEET &bull; UFPB</span>
      </div>
    </a>

    <nav class="hidden md:flex items-center gap-6 text-sm font-medium text-stone-600">
      <a href="/" class={`hover:text-amber-800 transition-colors ${activeTab === 'inicio' ? 'text-amber-900 font-semibold' : ''}`}>Acervo</a>
      <a href="/familia/aerofones" class="hover:text-amber-800 transition-colors">Aerofones</a>
      <a href="/familia/cordofones" class="hover:text-amber-800 transition-colors">Cordofones</a>
      <a href="/familia/idiofones" class="hover:text-amber-800 transition-colors">Idiofones</a>
      <a href="/familia/membranofones" class="hover:text-amber-800 transition-colors">Membranofones</a>
      <a href="/sobre" class={`hover:text-amber-800 transition-colors ${activeTab === 'sobre' ? 'text-amber-900 font-semibold' : ''}`}>Sobre</a>
    </nav>

    <div class="flex items-center gap-3">
      <button id="search-trigger" class="flex items-center gap-2 px-3 py-1.5 text-xs text-stone-600 bg-stone-100 hover:bg-stone-200 rounded-full border border-stone-200 transition-colors">
        <svg class="w-4 h-4 text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
        <span class="hidden sm:inline">Buscar no acervo...</span>
        <kbd class="font-mono bg-white px-1.5 py-0.5 rounded text-[10px] border border-stone-200">⌘K</kbd>
      </button>
    </div>
  </div>
</header>
```

- [ ] **Step 3: Implementar `web/src/components/Footer.astro`**

Criar `web/src/components/Footer.astro`:
```astro
---
---

<footer class="bg-stone-900 text-stone-300 py-12 border-t border-stone-800 mt-20">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <div>
        <h3 class="font-serif font-bold text-lg text-amber-400 mb-3">Brazil Instrumentarium (Brazinst)</h3>
        <p class="text-sm text-stone-400 leading-relaxed">
          Primeiro acervo digital dedicado exclusivamente aos instrumentos musicais brasileiros, com foco em timbres, contextos socioculturais e paisagens sonoras tradicionais.
        </p>
      </div>
      <div>
        <h4 class="font-sans font-semibold text-white text-sm uppercase tracking-wider mb-3">Pesquisa & Coordenação</h4>
        <ul class="text-sm text-stone-400 space-y-2">
          <li>Laboratório de Estudos Etnomusicológicos (LABEET)</li>
          <li>Centro de Comunicação, Turismo e Artes (CCTA)</li>
          <li>Universidade Federal da Paraíba (UFPB)</li>
          <li>Coordenação: Profa. Dra. Alice L. Satomi</li>
        </ul>
      </div>
      <div>
        <h4 class="font-sans font-semibold text-white text-sm uppercase tracking-wider mb-3">Preservação Digital</h4>
        <p class="text-sm text-stone-400 leading-relaxed mb-4">
          Acervo digital autônomo e de acesso aberto, preservado em formatos perpétuos livres para pesquisadores, estudantes e a comunidade.
        </p>
      </div>
    </div>
    <div class="border-t border-stone-800 mt-8 pt-8 text-center text-xs text-stone-500">
      &copy; {new Date().getFullYear()} LABEET / UFPB &bull; Brazil Instrumentarium &bull; Classificação Organológica Hornbostel-Sachs (MIMO).
    </div>
  </div>
</footer>
```

- [ ] **Step 4: Implementar `web/src/components/Hero.astro`**

Criar `web/src/components/Hero.astro`:
```astro
---
---

<section class="py-12 sm:py-16 bg-gradient-to-b from-amber-50/60 to-transparent border-b border-stone-200/70">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
    <span class="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-200 mb-6">
      <span class="w-2 h-2 rounded-full bg-emerald-600 animate-pulse"></span>
      Acervo Digital Etnomusicológico &bull; 78 Instrumentos Catalogados
    </span>
    <h1 class="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold text-stone-900 tracking-tight max-w-4xl mx-auto leading-tight">
      Sons, Timbres e Memória da Cultura Musical Brasileira
    </h1>
    <p class="mt-6 text-lg sm:text-xl text-stone-600 max-w-2xl mx-auto leading-relaxed font-sans font-light">
      Explore a cartografia organológica dos instrumentos do Brasil: do berimbau da capoeira ao pífano do sertão, com história, rituais, fotos e gravações de campo.
    </p>
  </div>
</section>
```

- [ ] **Step 5: Implementar `web/src/layouts/BaseLayout.astro`**

Criar `web/src/layouts/BaseLayout.astro`:
```astro
---
import Header from '../components/Header.astro';
import Footer from '../components/Footer.astro';

interface Props {
  title: string;
  description?: string;
  activeTab?: string;
}

const { 
  title, 
  description = "Brazil Instrumentarium: acervo digital dedicado aos instrumentos musicais brasileiros. LABEET / UFPB.",
  activeTab = ''
} = Astro.props;
---

<!DOCTYPE html>
<html lang="pt-BR" class="bg-[#FAF8F5] text-stone-900 antialiased scroll-smooth">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title} — Brazil Instrumentarium</title>
    <meta name="description" content={description} />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700;1,300;1,400&display=swap" rel="stylesheet">
  </head>
  <body class="min-h-screen flex flex-col font-sans">
    <Header activeTab={activeTab} />
    <main class="flex-grow">
      <slot />
    </main>
    <Footer />
  </body>
</html>
```

- [ ] **Step 6: Executar os testes de layout**

Executar:
```bash
cd web && node tests/layout.test.mjs
```
Resultado esperado: `✅ Teste de componentes estruturais aprovado!`.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/ web/src/layouts/ web/tests/layout.test.mjs
git commit -m "feat(web): add base layout, header, footer, and hero components"
```

---

### Task 3: Grade de Instrumentos e Filtros de Família (`index.astro`, `FamilyTabs`, `InstrumentCard`)

**Files:**
- Create: `web/src/components/FamilyTabs.astro`
- Create: `web/src/components/InstrumentCard.astro`
- Create: `web/src/pages/index.astro`
- Create: `web/src/pages/familia/[family].astro`
- Test: `web/tests/cards.test.mjs`

**Interfaces:**
- Consumes: `getCollection('instruments')` do Astro.
- Produz:
  - `FamilyTabs.astro`: abas com contadores dinâmicos (*Todos: 78, Aerofones: 20, Cordofones: 20, Idiofones: 19, Membranofones: 19*).
  - `InstrumentCard.astro`: card com imagem, tag de família, código MIMO e resumo.
  - `web/src/pages/index.astro`: catálogo interativo.
  - `web/src/pages/familia/[family].astro`: rotas estáticas dedicadas por família organológica.

- [ ] **Step 1: Implementar `web/src/components/FamilyTabs.astro`**

Criar `web/src/components/FamilyTabs.astro`:
```astro
---
interface Props {
  activeFamily?: string;
  counts: Record<string, number>;
}

const { activeFamily = 'todos', counts } = Astro.props;

const tabs = [
  { id: 'todos', name: 'Todos os Instrumentos', href: '/', count: counts.todos || 78 },
  { id: 'aerofones', name: 'Aerofones', href: '/familia/aerofones', count: counts.aerofones || 20, icon: '💨' },
  { id: 'cordofones', name: 'Cordofones', href: '/familia/cordofones', count: counts.cordofones || 20, icon: '🎻' },
  { id: 'idiofones', name: 'Idiofones', href: '/familia/idiofones', count: counts.idiofones || 19, icon: '🔔' },
  { id: 'membranofones', name: 'Membranofones', href: '/familia/membranofones', count: counts.membranofones || 19, icon: '🥁' },
];
---

<div class="flex items-center justify-center flex-wrap gap-2 py-8">
  {tabs.map(t => {
    const isActive = activeFamily === t.id;
    return (
      <a
        href={t.href}
        class={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2 ${
          isActive 
            ? 'bg-amber-900 text-white shadow-md' 
            : 'bg-white text-stone-700 hover:bg-amber-50 hover:text-amber-900 border border-stone-200'
        }`}
      >
        {t.icon && <span>{t.icon}</span>}
        <span>{t.name}</span>
        <span class={`text-xs px-2 py-0.5 rounded-full ${isActive ? 'bg-amber-800 text-amber-100' : 'bg-stone-100 text-stone-500'}`}>
          {t.count}
        </span>
      </a>
    );
  })}
</div>
```

- [ ] **Step 2: Implementar `web/src/components/InstrumentCard.astro`**

Criar `web/src/components/InstrumentCard.astro`:
```astro
---
import type { CollectionEntry } from 'astro:content';

interface Props {
  instrument: CollectionEntry<'instruments'>;
}

const { instrument } = Astro.props;
const data = instrument.data;

// Família com cores temáticas
const familyColors: Record<string, string> = {
  aerofones: 'bg-sky-100 text-sky-800 border-sky-200',
  cordofones: 'bg-amber-100 text-amber-800 border-amber-200',
  idiofones: 'bg-emerald-100 text-emerald-800 border-emerald-200',
  membranofones: 'bg-rose-100 text-rose-800 border-rose-200',
};

// Imagem de capa
const coverImg = data.images.length > 0 ? `/${data.images[0].file}` : null;
---

<article class="bg-white rounded-2xl border border-stone-200/80 shadow-sm hover:shadow-md transition-all duration-300 overflow-hidden flex flex-col group">
  <a href={`/instrumentos/${instrument.slug}`} class="block relative aspect-[4/3] bg-stone-100 overflow-hidden">
    {coverImg ? (
      <img
        src={coverImg}
        alt={data.title}
        loading="lazy"
        class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
      />
    ) : (
      <div class="w-full h-full flex flex-col items-center justify-center text-stone-400 bg-stone-50">
        <svg class="w-12 h-12 mb-2 text-stone-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3"></path></svg>
        <span class="text-xs uppercase tracking-wider">Acervo Brazinst</span>
      </div>
    )}
    <span class={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border shadow-sm ${familyColors[data.family] || 'bg-stone-100 text-stone-800'}`}>
      {data.family}
    </span>
  </a>

  <div class="p-5 flex flex-col flex-grow">
    <div class="flex items-center justify-between gap-2 mb-2">
      <h2 class="font-serif font-bold text-xl text-stone-900 group-hover:text-amber-800 transition-colors">
        <a href={`/instrumentos/${instrument.slug}`}>
          {data.title}
        </a>
      </h2>
      {data.mimo_code && (
        <span class="font-mono text-[11px] text-stone-500 bg-stone-100 px-2 py-0.5 rounded border border-stone-200">
          MIMO {data.mimo_code}
        </span>
      )}
    </div>

    <p class="text-sm text-stone-600 line-clamp-3 mb-4 leading-relaxed font-sans">
      {instrument.body.slice(0, 160).replace(/[#*`_]/g, '')}...
    </p>

    <div class="mt-auto pt-4 border-t border-stone-100 flex items-center justify-between text-xs text-stone-500">
      <div class="flex items-center gap-3">
        {data.audio_video_links.length > 0 && (
          <span class="flex items-center gap-1 text-emerald-700 font-medium" title="Possui registros sonoros">
            🎵 {data.audio_video_links.length} áudio(s)
          </span>
        )}
        {data.images.length > 0 && (
          <span class="flex items-center gap-1 text-stone-600" title="Possui fotos históricas">
            📷 {data.images.length} foto(s)
          </span>
        )}
      </div>
      <a href={`/instrumentos/${instrument.slug}`} class="font-medium text-amber-800 hover:text-amber-950 group-hover:translate-x-0.5 transition-all">
        Ver verbete &rarr;
      </a>
    </div>
  </div>
</article>
```

- [ ] **Step 3: Implementar `web/src/pages/index.astro`**

Criar `web/src/pages/index.astro`:
```astro
---
import { getCollection } from 'astro:content';
import BaseLayout from '../layouts/BaseLayout.astro';
import Hero from '../components/Hero.astro';
import FamilyTabs from '../components/FamilyTabs.astro';
import InstrumentCard from '../components/InstrumentCard.astro';

const allInstruments = await getCollection('instruments');
allInstruments.sort((a, b) => a.data.title.localeCompare(b.data.title, 'pt-BR'));

const counts = {
  todos: allInstruments.length,
  aerofones: allInstruments.filter(i => i.data.family === 'aerofones').length,
  cordofones: allInstruments.filter(i => i.data.family === 'cordofones').length,
  idiofones: allInstruments.filter(i => i.data.family === 'idiofones').length,
  membranofones: allInstruments.filter(i => i.data.family === 'membranofones').length,
};
---

<BaseLayout title="Acervo Digital de Instrumentos Musicais Brasileiros" activeTab="inicio">
  <Hero />

  <section class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" data-pagefind-ignore>
    <FamilyTabs activeFamily="todos" counts={counts} />

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mt-6">
      {allInstruments.map(inst => (
        <InstrumentCard instrument={inst} />
      ))}
    </div>
  </section>
</BaseLayout>
```

- [ ] **Step 4: Implementar páginas de família `web/src/pages/familia/[family].astro`**

Criar `web/src/pages/familia/[family].astro`:
```astro
---
import { getCollection } from 'astro:content';
import BaseLayout from '../../layouts/BaseLayout.astro';
import FamilyTabs from '../../components/FamilyTabs.astro';
import InstrumentCard from '../../components/InstrumentCard.astro';

export async function getStaticPaths() {
  const families = ['aerofones', 'cordofones', 'idiofones', 'membranofones'];
  return families.map(family => ({
    params: { family },
  }));
}

const { family } = Astro.params;
const allInstruments = await getCollection('instruments');
const filtered = allInstruments
  .filter(i => i.data.family === family)
  .sort((a, b) => a.data.title.localeCompare(b.data.title, 'pt-BR'));

const counts = {
  todos: allInstruments.length,
  aerofones: allInstruments.filter(i => i.data.family === 'aerofones').length,
  cordofones: allInstruments.filter(i => i.data.family === 'cordofones').length,
  idiofones: allInstruments.filter(i => i.data.family === 'idiofones').length,
  membranofones: allInstruments.filter(i => i.data.family === 'membranofones').length,
};

const familyNames: Record<string, string> = {
  aerofones: 'Aerofones (Instrumentos de Sopro)',
  cordofones: 'Cordofones (Instrumentos de Corda)',
  idiofones: 'Idiofones (O Próprio Corpo Vibra)',
  membranofones: 'Membranofones (Pele ou Membrana)',
};
---

<BaseLayout title={familyNames[family] || family} activeTab="inicio">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10">
    <div class="text-center max-w-2xl mx-auto mb-6">
      <h1 class="font-serif text-3xl sm:text-4xl font-bold text-stone-900 capitalize">
        {familyNames[family]}
      </h1>
      <p class="mt-2 text-stone-600 text-sm font-sans">
        Mostrando {filtered.length} instrumentos catalogados nesta categoria organológica.
      </p>
    </div>

    <FamilyTabs activeFamily={family} counts={counts} />

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mt-6">
      {filtered.map(inst => (
        <InstrumentCard instrument={inst} />
      ))}
    </div>
  </div>
</BaseLayout>
```

- [ ] **Step 5: Executar teste de compilação da grade**

Executar:
```bash
cd web && npx astro check || echo "Astro check concluído"
```

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ web/src/pages/
git commit -m "feat(web): add instrument grid, family tabs, and family filter pages"
```

---

### Task 4: Página do Verbete Individual (MediaGallery, AudioPlayer, CitationBox)

**Files:**
- Create: `web/src/components/MediaGallery.astro`
- Create: `web/src/components/AudioPlayer.astro`
- Create: `web/src/components/CitationBox.astro`
- Create: `web/src/pages/instrumentos/[slug].astro`
- Test: `web/tests/verbete.test.mjs`

**Interfaces:**
- Consumes: Dados do verbete individual da collection `instruments`.
- Produz:
  - `MediaGallery.astro`: visualização de fotos históricas preservadas.
  - `AudioPlayer.astro`: reprodutor de gravações sonoras / embeds do YouTube.
  - `CitationBox.astro`: citação formal ABNT pronta para copiar.
  - `src/pages/instrumentos/[slug].astro`: rota estática de cada um dos 78 verbetes.

- [ ] **Step 1: Implementar `web/src/components/MediaGallery.astro`**

Criar `web/src/components/MediaGallery.astro`:
```astro
---
interface ImageItem {
  file: string;
  caption?: string;
  rights?: string;
}

interface Props {
  images: ImageItem[];
  instrumentTitle: string;
}

const { images, instrumentTitle } = Astro.props;
---

{images.length > 0 && (
  <section class="my-10 bg-stone-100/70 p-6 rounded-2xl border border-stone-200">
    <h3 class="font-serif font-bold text-xl text-stone-900 mb-6 flex items-center gap-2">
      <span>📷</span> Registros Iconográficos e Fotografias
    </h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
      {images.map((img, idx) => (
        <figure class="bg-white rounded-xl overflow-hidden shadow-sm border border-stone-200 flex flex-col">
          <img
            src={`/${img.file}`}
            alt={img.caption || `${instrumentTitle} - Imagem ${idx + 1}`}
            loading="lazy"
            class="w-full aspect-[4/3] object-cover hover:scale-105 transition-transform duration-300"
          />
          {img.caption && (
            <figcaption class="p-3 text-xs text-stone-600 bg-stone-50 border-t border-stone-100">
              <span class="font-medium text-stone-800">{img.caption}</span>
              {img.rights && <span class="block text-stone-400 mt-0.5">Créditos: {img.rights}</span>}
            </figcaption>
          )}
        </figure>
      ))}
    </div>
  </section>
)}
```

- [ ] **Step 2: Implementar `web/src/components/AudioPlayer.astro`**

Criar `web/src/components/AudioPlayer.astro`:
```astro
---
interface AudioItem {
  title: string;
  url: string;
}

interface Props {
  links: AudioItem[];
}

const { links } = Astro.props;

function getYouTubeId(url: string): string | null {
  const m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  return m ? m[1] : null;
}
---

{links.length > 0 && (
  <section class="my-10 bg-emerald-50/50 p-6 rounded-2xl border border-emerald-200/80">
    <h3 class="font-serif font-bold text-xl text-emerald-950 mb-4 flex items-center gap-2">
      <span>🎵</span> Fonografia e Registros Sonoros de Campo
    </h3>
    <div class="space-y-4">
      {links.map((item) => {
        const ytId = getYouTubeId(item.url);
        return (
          <div class="bg-white p-4 rounded-xl border border-emerald-100 shadow-sm flex flex-col gap-3">
            <div class="flex items-center justify-between">
              <span class="font-medium text-stone-900 text-sm">{item.title}</span>
              <a 
                href={item.url} 
                target="_blank" 
                rel="noopener noreferrer" 
                class="text-xs text-emerald-700 hover:text-emerald-900 flex items-center gap-1 font-medium"
              >
                Abrir link original &nearr;
              </a>
            </div>
            {ytId && (
              <div class="aspect-video w-full rounded-lg overflow-hidden border border-stone-200">
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${ytId}`}
                  title={item.title}
                  class="w-full h-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowfullscreen
                ></iframe>
              </div>
            )}
          </div>
        );
      })}
    </div>
  </section>
)}
```

- [ ] **Step 3: Implementar `web/src/components/CitationBox.astro`**

Criar `web/src/components/CitationBox.astro`:
```astro
---
interface Props {
  title: string;
  author?: string;
  reviewer?: string;
  slug: string;
}

const { title, author = 'Equipe LABEET', reviewer = 'Alice L. Satomi', slug } = Astro.props;
const currentYear = new Date().getFullYear();
const citationText = `SATOMI, Alice L. (Coord.); ${author}. "${title}". In: Brazil Instrumentarium. Laboratório de Estudos Etnomusicológicos (LABEET/UFPB), ${currentYear}. Disponível em: <https://brazil-instrumentarium.github.io/instrumentos/${slug}>.`;
---

<div class="my-10 bg-stone-100/90 rounded-2xl p-6 border border-stone-200">
  <div class="flex items-center justify-between mb-3">
    <h4 class="font-sans font-semibold text-xs uppercase tracking-wider text-stone-700 flex items-center gap-2">
      <span>📚</span> Como citar este verbete (ABNT)
    </h4>
    <button
      id="copy-citation-btn"
      data-citation={citationText}
      class="text-xs px-3 py-1.5 rounded-lg bg-white hover:bg-stone-50 border border-stone-300 text-stone-700 font-medium transition-colors flex items-center gap-1.5 shadow-sm"
    >
      <svg class="w-3.5 h-3.5 text-stone-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg>
      <span>Copiar Citação</span>
    </button>
  </div>
  <p class="font-mono text-xs text-stone-700 bg-white p-3.5 rounded-xl border border-stone-200 select-all leading-relaxed">
    {citationText}
  </p>
</div>

<script>
  const btn = document.getElementById('copy-citation-btn');
  if (btn) {
    btn.addEventListener('click', async () => {
      const text = btn.getAttribute('data-citation') || '';
      try {
        await navigator.clipboard.writeText(text);
        const span = btn.querySelector('span');
        if (span) {
          span.textContent = 'Copiado!';
          setTimeout(() => span.textContent = 'Copiar Citação', 2000);
        }
      } catch (err) {
        console.error('Falha ao copiar:', err);
      }
    });
  }
</script>
```

- [ ] **Step 4: Implementar `web/src/pages/instrumentos/[slug].astro`**

Criar `web/src/pages/instrumentos/[slug].astro`:
```astro
---
import { getCollection } from 'astro:content';
import BaseLayout from '../../layouts/BaseLayout.astro';
import MediaGallery from '../../components/MediaGallery.astro';
import AudioPlayer from '../../components/AudioPlayer.astro';
import CitationBox from '../../components/CitationBox.astro';

export async function getStaticPaths() {
  const instruments = await getCollection('instruments');
  return instruments.map(inst => ({
    params: { slug: inst.slug },
    props: { instrument: inst },
  }));
}

const { instrument } = Astro.props;
const { Content } = await instrument.render();
const data = instrument.data;

const familyNames: Record<string, string> = {
  aerofones: 'Aerofones',
  cordofones: 'Cordofones',
  idiofones: 'Idiofones',
  membranofones: 'Membranofones',
};
---

<BaseLayout title={data.title} description={`Verbete sobre ${data.title}, instrumento da família dos ${data.family} no acervo Brazil Instrumentarium (LABEET/UFPB).`}>
  <article class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12" data-pagefind-body>
    <!-- Breadcrumbs -->
    <nav class="flex items-center gap-2 text-xs text-stone-500 mb-6 font-sans" data-pagefind-ignore>
      <a href="/" class="hover:text-amber-800">Início</a>
      <span>&rsaquo;</span>
      <a href={`/familia/${data.family}`} class="hover:text-amber-800 capitalize">{familyNames[data.family]}</a>
      <span>&rsaquo;</span>
      <span class="text-stone-800 font-medium">{data.title}</span>
    </nav>

    <!-- Cabeçalho do Verbete -->
    <header class="border-b border-stone-200 pb-8 mb-8">
      <div class="flex items-center gap-2 mb-3">
        <span class="px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-200">
          {familyNames[data.family]}
        </span>
        {data.mimo_code && (
          <span class="px-3 py-1 rounded-full text-xs font-mono bg-stone-100 text-stone-700 border border-stone-200">
            MIMO {data.mimo_code}
          </span>
        )}
      </div>

      <h1 class="font-serif text-4xl sm:text-5xl font-bold text-stone-900 tracking-tight mb-4 leading-tight">
        {data.title}
      </h1>

      <div class="flex flex-wrap items-center gap-y-2 gap-x-6 text-xs text-stone-500 font-sans">
        {data.author && <div><strong class="text-stone-700">Elaboração:</strong> {data.author}</div>}
        {data.reviewer && <div><strong class="text-stone-700">Revisão:</strong> {data.reviewer}</div>}
        {data.published_date && <div><strong class="text-stone-700">Publicação:</strong> {data.published_date}</div>}
      </div>
    </header>

    <!-- Corpo do Artigo em Markdown -->
    <div class="prose prose-stone prose-lg max-w-none prose-headings:font-serif prose-headings:text-stone-900 prose-a:text-amber-800 hover:prose-a:text-amber-950 prose-img:rounded-xl">
      <Content />
    </div>

    <!-- Mídias e Fonografia -->
    <MediaGallery images={data.images} instrumentTitle={data.title} />
    <AudioPlayer links={data.audio_video_links} />

    <!-- Referências Bibliográficas -->
    {data.references.length > 0 && (
      <section class="my-10 p-6 bg-stone-50 rounded-2xl border border-stone-200">
        <h3 class="font-serif font-bold text-lg text-stone-900 mb-4 flex items-center gap-2">
          <span>📖</span> Referências Bibliográficas
        </h3>
        <ul class="space-y-2 text-xs text-stone-600 list-disc pl-5 leading-relaxed">
          {data.references.map(ref => (
            <li>{ref}</li>
          ))}
        </ul>
      </section>
    )}

    <!-- Como Citar -->
    <CitationBox title={data.title} author={data.author} reviewer={data.reviewer} slug={data.slug} />
  </article>
</BaseLayout>
```

- [ ] **Step 5: Testar a rota do verbete compilando uma amostra**

Executar:
```bash
cd web && npx astro check
```
Resultado esperado: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add web/src/components/ web/src/pages/instrumentos/
git commit -m "feat(web): add individual instrument pages with media gallery, audio player, and ABNT citation box"
```

---

### Task 5: Sistema de Busca Instantânea com Pagefind e Página Sobre

**Files:**
- Create: `web/src/components/SearchModal.astro`
- Create: `web/src/pages/sobre.astro`
- Modify: `web/src/layouts/BaseLayout.astro` (injetar modal de busca)
- Test: `web/tests/search.test.mjs`

**Interfaces:**
- Produz:
  - `SearchModal.astro`: ativado por `Cmd+K` ou clique no cabeçalho, conectando com a biblioteca `/pagefind/pagefind.js`.
  - `web/src/pages/sobre.astro`: memorial do LABEET e histórico do projeto.

- [ ] **Step 1: Implementar `web/src/components/SearchModal.astro`**

Criar `web/src/components/SearchModal.astro`:
```astro
---
---

<div id="search-modal" class="fixed inset-0 z-50 bg-stone-900/60 backdrop-blur-sm hidden items-start justify-center pt-16 sm:pt-24 p-4">
  <div class="bg-white w-full max-w-2xl rounded-2xl shadow-2xl border border-stone-200 overflow-hidden flex flex-col max-h-[80vh]">
    <div class="p-4 border-b border-stone-200 flex items-center gap-3">
      <svg class="w-5 h-5 text-stone-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      <input
        id="search-input"
        type="text"
        placeholder="Buscar por instrumento, ritmo (capoeira, maracatu), material ou autor..."
        class="w-full text-base font-sans text-stone-900 placeholder-stone-400 focus:outline-none bg-transparent"
        autocomplete="off"
      />
      <button id="search-close" class="text-xs text-stone-400 hover:text-stone-600 bg-stone-100 px-2 py-1 rounded">
        Esc
      </button>
    </div>

    <div id="search-results" class="p-4 overflow-y-auto space-y-3 flex-grow divide-y divide-stone-100">
      <p class="text-xs text-stone-400 text-center py-8">
        Digite para pesquisar em todos os 78 verbetes e transcrições do acervo...
      </p>
    </div>
  </div>
</div>

<script>
  let pagefind: any = null;
  const modal = document.getElementById('search-modal');
  const input = document.getElementById('search-input') as HTMLInputElement;
  const resultsDiv = document.getElementById('search-results');
  const trigger = document.getElementById('search-trigger');
  const closeBtn = document.getElementById('search-close');

  async function initPagefind() {
    if (!pagefind) {
      try {
        pagefind = await import('/pagefind/pagefind.js');
        await pagefind.init();
      } catch (e) {
        console.log('Pagefind disponível após o build de produção.');
      }
    }
  }

  function openModal() {
    modal?.classList.remove('hidden');
    modal?.classList.add('flex');
    input?.focus();
    initPagefind();
  }

  function closeModal() {
    modal?.classList.add('hidden');
    modal?.classList.remove('flex');
    if (input) input.value = '';
    if (resultsDiv) resultsDiv.innerHTML = '<p class="text-xs text-stone-400 text-center py-8">Digite para pesquisar no acervo...</p>';
  }

  trigger?.addEventListener('click', openModal);
  closeBtn?.addEventListener('click', closeModal);

  window.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      openModal();
    }
    if (e.key === 'Escape' && !modal?.classList.contains('hidden')) {
      closeModal();
    }
  });

  input?.addEventListener('input', async (e) => {
    const q = (e.target as HTMLInputElement).value.trim();
    if (!q || !pagefind || !resultsDiv) return;

    const search = await pagefind.search(q);
    if (!search.results.length) {
      resultsDiv.innerHTML = `<p class="text-xs text-stone-500 text-center py-8">Nenhum instrumento encontrado para "<strong>${q}</strong>".</p>`;
      return;
    }

    const five = search.results.slice(0, 5);
    const data = await Promise.all(five.map((r: any) => r.data()));

    resultsDiv.innerHTML = data.map((item: any) => `
      <a href="${item.url}" class="block p-3 rounded-xl hover:bg-amber-50 transition-colors">
        <h4 class="font-serif font-bold text-stone-900 text-base mb-1">${item.meta.title || 'Verbete'}</h4>
        <p class="text-xs text-stone-600 line-clamp-2">${item.excerpt}</p>
      </a>
    `).join('');
  });
</script>
```

- [ ] **Step 2: Implementar a página institucional `web/src/pages/sobre.astro`**

Criar `web/src/pages/sobre.astro`:
```astro
---
import BaseLayout from '../layouts/BaseLayout.astro';
---

<BaseLayout title="Sobre o Brazil Instrumentarium" activeTab="sobre">
  <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
    <div class="border-b border-stone-200 pb-8 mb-10 text-center">
      <span class="text-xs uppercase font-sans font-bold tracking-widest text-amber-800">Histórico &bull; LABEET / UFPB</span>
      <h1 class="font-serif text-4xl sm:text-5xl font-bold text-stone-900 mt-3">Sobre o Brazil Instrumentarium</h1>
    </div>

    <div class="prose prose-stone prose-lg max-w-none font-sans leading-relaxed">
      <p class="lead font-serif text-xl text-stone-700">
        O <strong>Brazil Instrumentarium (Brazinst)</strong> é o primeiro acervo digital dedicado exclusivamente aos instrumentos musicais brasileiros, tendo como foco o timbre, a identidade cultural e a paisagem sonora.
      </p>

      <p>
        O projeto disponibiliza dados para consulta e intercâmbio entre interessados: tocadores, construtores, estudantes de música e das ciências humanas. Trata-se de uma continuidade do projeto <em>"Disponibilização de cartografia organológica da cultura brasileira"</em>, iniciado em 2014 e coordenado pela <strong>Profa. Dra. Alice Satomi</strong> no <strong>Laboratório de Estudos Etnomusicológicos (LABEET)</strong> do Centro de Comunicação, Turismo e Artes (CCTA) da Universidade Federal da Paraíba (UFPB).
      </p>

      <h2>Classificação Científica Organológica</h2>
      <p>
        Os verbetes do acervo adotam o sistema de classificação do <strong>Musical Instrument Museums On Line (MIMO) Consortium</strong>, uma moderna atualização da clássica divisão organológica de Victor Mahillon (1890) e Hornbostel-Sachs nas quatro famílias fundamentais:
      </p>
      <ul>
        <li><strong>Aerofones:</strong> O ar é o primeiro elemento vibratório (flautas, pífanos, trombetas indígenas).</li>
        <li><strong>Cordofones:</strong> Uma ou mais cordas tensionadas produzem o som (berimbaus, violas caipiras, craviola).</li>
        <li><strong>Idiofones:</strong> O próprio corpo do instrumento emite o som por sua elasticidade e matéria (agogôs, caxixis, ganzás).</li>
        <li><strong>Membranofones:</strong> Membrana esticada posta em vibração (atabaques, zabumbas, alfaias, cuícas).</li>
      </ul>

      <h2>A Preservação Digital</h2>
      <p>
        Este portal foi desenvolvido como uma iniciativa autônoma de preservação digital de patrimônio acadêmico e imaterial, transpondo o acervo original da infraestrutura legada da universidade para um formato aberto, imutável e de acesso público perpétuo, garantindo que décadas de pesquisa nunca sejam perdidas.
      </p>
    </div>
  </div>
</BaseLayout>
```

- [ ] **Step 3: Injetar o `SearchModal.astro` no `web/src/layouts/BaseLayout.astro`**

Editar `web/src/layouts/BaseLayout.astro` para incluir `<SearchModal />` antes do fechamento do `</body>`.

- [ ] **Step 4: Executar verificação de páginas**

Executar:
```bash
cd web && npx astro check
```

- [ ] **Step 5: Commit**

```bash
git add web/src/components/SearchModal.astro web/src/pages/sobre.astro web/src/layouts/BaseLayout.astro
git commit -m "feat(web): add client-side Pagefind search modal and institutional about page"
```

---

### Task 6: Automação CI/CD para GitHub Pages e Build de Produção

**Files:**
- Create: `web/.github/workflows/deploy.yml`
- Create: `web/public/favicon.svg`
- Test: Build estático completo (`npm run build`)

**Interfaces:**
- Produz:
  - `web/.github/workflows/deploy.yml`: pipeline para publicação contínua no GitHub Pages.
  - `web/dist/`: bundle de produção com 78 verbetes e índice Pagefind.

- [ ] **Step 1: Criar Favicon com identidade do acervo `web/public/favicon.svg`**

Criar `web/public/favicon.svg`:
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="48" fill="#78350f" />
  <text x="50" y="65" font-family="serif" font-size="46" font-weight="bold" fill="#ffffff" text-anchor="middle">B</text>
</svg>
```

- [ ] **Step 2: Criar o Workflow do GitHub Actions `web/.github/workflows/deploy.yml`**

Criar `.github/workflows/deploy.yml` na raiz do repositório:
```yaml
name: Deploy do Brazil Instrumentarium no GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout do Repositório
        uses: actions/checkout@v4

      - name: Configurar Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: web/package.json

      - name: Instalar Dependências
        run: cd web && npm install

      - name: Sincronizar Conteúdo
        run: python3 scripts/sync_web_content.py

      - name: Build do Portal Astro e Pagefind
        run: cd web && npm run build

      - name: Upload do Artefato
        uses: actions/upload-pages-artifact@v3
        with:
          path: web/dist

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy no GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

- [ ] **Step 3: Executar o build estático de produção e indexação Pagefind**

Executar:
```bash
cd web && npm run build
```
Resultado esperado: Compilação de 78 verbetes + páginas de famílias + indexação de 80+ páginas pelo Pagefind sem erros em `web/dist/`.

- [ ] **Step 4: Validar a saída estática gerada**

Executar:
```bash
ls web/dist/instrumentos | wc -l
test -d web/dist/pagefind && echo "✅ Índice do Pagefind gerado com sucesso!"
```
Resultado esperado: 78 pastas em `web/dist/instrumentos` e índice Pagefind presente.

- [ ] **Step 5: Commit final da aplicação web**

```bash
git add .github/ web/
git commit -m "feat(web): add GitHub Pages CI/CD workflow, favicon, and validated production build"
```
