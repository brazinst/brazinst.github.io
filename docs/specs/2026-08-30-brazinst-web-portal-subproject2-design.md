# Especificação de Design: Novo Portal Web do Brazil Instrumentarium (Brazinst)

**Data:** 2026-08-30  
**Status:** Em Revisão  
**Escopo:** Sub-projeto 2 — Portal Web Moderno, Independente e de Custo Zero  

---

## 1. Contexto e Objetivos

Com a conclusão com êxito do **Sub-projeto 1** (preservação do site legado da UFPB e extração semântica limpa de 78 verbetes de instrumentos musicais brasileiros em Markdown com metadados YAML e fotos em alta resolução), o objetivo do **Sub-projeto 2** é dar um novo lar definitivo e moderno a essa pesquisa etnomusicológica.

O **Brazil Instrumentarium (Brazinst)**, idealizado e coordenado pela Profa. Dra. Alice Satomi no LABEET (Laboratório de Estudos Etnomusicológicos da UFPB), é o primeiro acervo digital dedicado exclusivamente aos instrumentos musicais brasileiros com base na classificação organológica Hornbostel-Sachs (MIMO Consortium).

### Objetivos do Sub-projeto 2:
1. **Portal Web Rápido e Moderno:** Desenvolver uma aplicação web estática usando **Astro + Tailwind CSS**, otimizada para dispositivos móveis e desktops, com design caloroso, editorial e cultural.
2. **Custo Zero Perpétuo:** Eliminar qualquer dependência de servidores institucionais ou bancos de dados gerenciados, garantindo hospedagem 100% gratuita para sempre via **GitHub Pages** (ou Cloudflare Pages).
3. **Busca Instantânea Inteligente (Pagefind):** Permitir buscas estáticas ultrarrápidas no navegador por nomes de instrumentos, materiais (*bambu, cabaça, couro*), manifestações populares (*capoeira, maracatu, xangô, samba de roda, bandas de pífano*) ou códigos organológicos MIMO.
4. **Experiência Visual e Sonora Rica:** Disponibilizar players embutidos para as gravações de fonografia (YouTube e áudios de campo) e galerias com fotos históricas (como Mestre Pastinha, Almir Sater, etc.).
5. **Rigor Acadêmico e Citação em 1 Clique:** Disponibilizar fichas catalográficas detalhadas e caixa de citação no padrão ABNT com botão de cópia instantânea para pesquisadores e estudantes.

---

## 2. Estrutura de Diretórios da Aplicação Web

O projeto será mantido no subdiretório `web/` do repositório local `/Users/gregoriomelo/dev/labeet`:

```text
/Users/gregoriomelo/dev/labeet/
├── backup_full/                  # Preservação bruta do site original (100% offline)
├── content_brazinst/             # Fonte primária dos dados limpos (78 verbetes)
│   ├── instruments/              # Arquivos Markdown categorizados por família
│   ├── media/                    # Fotos originais preservadas
│   └── brazinst_catalog.json     # Catálogo consolidado
├── docs/
│   └── specs/
│       ├── 2026-08-29-labeet-preservation-subproject1-design.md
│       └── 2026-08-30-brazinst-web-portal-subproject2-design.md
└── web/                          # APLICAÇÃO WEB ASTRO + TAILWIND
    ├── .github/
    │   └── workflows/
    │       └── deploy.yml        # CI/CD para build e deploy no GitHub Pages
    ├── public/
    │   ├── media/                # Fotos dos instrumentos copiadas/acessíveis para o build
    │   └── favicon.svg           # Ícone do acervo
    ├── src/
    │   ├── content/
    │   │   ├── config.ts         # Schema de validação Zod das Content Collections
    │   │   └── instruments/      # Os 78 arquivos Markdown sincronizados
    │   │       ├── aerofones/
    │   │       ├── cordofones/
    │   │       ├── idiofones/
    │   │       └── membranofones/
    │   ├── components/
    │   │   ├── Header.astro      # Navegação superior e atalho de busca
    │   │   ├── Hero.astro        # Apresentação do projeto e contextualização UFPB
    │   │   ├── FamilyTabs.astro  # Filtros visuais por família organológica
    │   │   ├── InstrumentCard.astro # Card do instrumento com foto e badges
    │   │   ├── MediaGallery.astro   # Galeria de fotos históricas em alta resolução
    │   │   ├── AudioPlayer.astro    # Player de fonografia e embeds leves
    │   │   ├── CitationBox.astro    # Caixa de citação ABNT com botão de cópia
    │   │   ├── SearchModal.astro # Modal de busca instantânea com Pagefind
    │   │   └── Footer.astro      # Rodapé com créditos institucionais ao LABEET
    │   ├── layouts/
    │   │   ├── BaseLayout.astro  # Layout global com metatags OpenGraph e SEO
    │   │   └── VerbeteLayout.astro # Layout para a página de leitura do verbete
    │   └── pages/
    │       ├── index.astro       # Catálogo geral com busca e grade de instrumentos
    │       ├── sobre.astro       # História do projeto, Profa. Alice Satomi e bolsistas
    │       ├── familia/
    │       │   └── [family].astro # Páginas filtradas por família organológica
    │       └── instrumentos/
    │           └── [slug].astro   # Página individual do verbete
    ├── astro.config.mjs
    ├── tailwind.config.mjs
    └── package.json
```

---

## 3. Esquema de Validação de Dados (Zod / Astro Content Collections)

O arquivo `web/src/content/config.ts` valida em tempo de compilação todos os 78 verbetes:

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

---

## 4. Componentes da Interface e Experiência do Usuário

### 4.1. Cores e Identidade Visual (Tailwind)
* **Paleta Cultural Brasileira:**
  * Primária: Tons de terra e madeira (`amber-800`, `amber-900`, `stone-900`).
  * Secundária / Destaques: Verde folha natural (`emerald-700`) e dourado suave (`yellow-600`).
  * Fundo: Creme suave de leitura (`bg-stone-50` / `bg-[#FAF8F5]`).
* **Tipografia:** Família serifada clássica para títulos (`Merriweather` ou `Playfair`) e sem serifa moderna e limpa para leitura de corpo de texto (`Inter` / `system-ui`).

### 4.2. Página Inicial (`index.astro`)
* **Hero Banner:** Introdução poética e científica ao acervo, destacando o pioneirismo do LABEET / UFPB no mapeamento organológico nacional.
* **Barra de Busca com Atalho:** Campo acessível que abre o modal de busca com `Cmd+K` / `Ctrl+K`.
* **Abas de Famílias (`FamilyTabs.astro`):**
  * *Todos* (78 instrumentos)
  * *Aerofones* (20 instrumentos) — Flautas, pífanos, trombetas
  * *Cordofones* (20 instrumentos) — Berimbaus, violas, craviola, bandolins
  * *Idiofones* (19 instrumentos) — Agogôs, caxixis, ganzás, reco-recos
  * *Membranofones* (19 instrumentos) — Atabaques, alfaias, zabumbas, cuícas
* **Cards de Instrumentos (`InstrumentCard.astro`):**
  * Imagem de capa com carregamento otimizado (`loading="lazy"`).
  * Tag de família com cores temáticas distintas.
  * Código de classificação Hornbostel-Sachs (MIMO).
  * Trecho inicial do texto contextual.
  * Indicadores de recursos: 🎵 *Fonografia*, 📷 *Galeria*.

### 4.3. Verbete do Instrumento (`instrumentos/[slug].astro`)
* **Navegação (Breadcrumbs):** *Início > [Família] > [Nome do Instrumento]*.
* **Ficha Organológica:** Metadados destacados com código MIMO e revisão científica.
* **Corpo do Artigo:** Formatação com Tailwind Typography (`prose prose-stone`) preservando parágrafos, listas e citações.
* **Galeria de Fotos Históricas (`MediaGallery.astro`):** Imagens com legendas informativas e visualizador ampliado.
* **Player de Fonografia (`AudioPlayer.astro`):** Suporte nativo a áudios locais (.mp3) e incorporação de vídeos do YouTube com thumbnail de carregamento sob demanda (sem travar a página).
* **Caixa de Citação ABNT (`CitationBox.astro`):** Formata automaticamente a citação:
  > `SATOMI, Alice L. et al. [Título do Instrumento]. In: Brazil Instrumentarium. Laboratório de Estudos Etnomusicológicos (LABEET/UFPB), 2026. Disponível em: <URL>.`
  Com botão interativo *"Copiar Citação ABNT"*.
* **Paginação Sequencial:** Navegação direta para o próximo e anterior instrumento da mesma família.

### 4.4. Página Sobre (`sobre.astro`)
* Contextualização histórica do acervo iniciado em 1995 por Alice Satomi, o projeto de cartografia de 2014, colaboração com o *The Grove Dictionary of Musical Instruments* e os bolsistas e pesquisadores voluntários.

---

## 5. Mecanismo de Busca Estática (Pagefind)

* **Sem Servidor (Client-Side Search):** O Pagefind é executado no build (`npx pagefind --site dist`). Ele lê os HTMLs gerados e produz arquivos estáticos pré-calculados.
* **Busca Contextual Profunda:** Permite pesquisar por termos no título, tags, autores e em qualquer parágrafo dos 78 verbetes.
* **Destaque de Trechos:** Apresenta na tela o parágrafo exato onde o termo foi encontrado com realce em negrito.

---

## 6. Automação de CI/CD e Deploy no GitHub Pages

O arquivo `web/.github/workflows/deploy.yml` gerencia a publicação perpétua a custo zero:

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
          cache-dependency-path: web/package-lock.json

      - name: Instalar Dependências
        run: cd web && npm ci

      - name: Build do Portal Astro e Índice Pagefind
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

---

## 7. Critérios de Sucesso e Validação

1. **Build Estático Limpo:** `npm run build` deve compilar 100% das páginas sem erros de validação Zod.
2. **78 Verbetes Acessíveis:** Todas as 78 páginas de instrumentos devem ser geradas em `/instrumentos/[slug]/` com conteúdo legível e ficha técnica.
3. **Mídias e Fotos Carregando:** Todas as fotos históricas preservadas devem ser servidas e exibidas corretamente nas páginas dos verbetes correspondentes.
4. **Busca Instantânea Funcional:** Pesquisas por termos como *"berimbau"*, *"capoeira"*, *"maracatu"* ou *"pífano"* devem retornar os resultados esperados com trechos correspondentes.
5. **Responsividade:** Navegação fluida em telas mobile (smartphones) e desktop.
6. **Relatório de Auditoria Final:** Relatório confirmando que nenhum instrumento ou imagem do acervo foi deixado de fora do novo portal.
