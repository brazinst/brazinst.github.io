# Brazil Instrumentarium (LABEET / UFPB)

Acervo digital e catálogo etnomusicológico dos instrumentos musicais da diversidade brasileira, desenvolvido pelo Laboratório de Estudos Etnomusicológicos (LABEET / CCTA / UFPB) sob coordenação da Profª. Drª. Alice Lumi Satomi.

O portal cataloga 165+ verbetes com classificação organológica Hornbostel-Sachs (MIMO), registros iconográficos, transcrições, fonografia e remissões tipológicas.

---

## Execução Local

### Pré-requisitos
- Node.js 20+
- Python 3.10+

### Comandos

```bash
# Dependências e execução da aplicação web
cd web && npm install
npm run dev

# Build de produção e indexação Pagefind
npm run build

# Testes da aplicação web
npm test
```

Para executar a suíte de testes Python:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

---

## Como Contribuir com Instrumentos

O catálogo é mantido em arquivos Markdown com frontmatter YAML em `web/src/content/instruments/`.

### 1. Famílias Organológicas
- `aerofones/`: Instrumentos de sopro (flautas, trombetas, apitos).
- `cordofones/`: Instrumentos de corda (violas, rabecas, berimbaus).
- `idiofones/`: Instrumentos cujo próprio corpo produz o som (chocalhos, reco-recos).
- `membranofones/`: Instrumentos de membrana tensionada (tambores, caixas, cuícas).

### 2. Template de Verbete
Crie o arquivo `web/src/content/instruments/<familia>/<slug>.md`:

```yaml
---
title: "Nome do Instrumento"
slug: "nome-do-instrumento"
family: "idiofones" # aerofones | cordofones | idiofones | membranofones
subtitle: null
description: "Descrição concisa e classificação organológica."
mimo_code: "1.1.2.1.1" # Classificação Hornbostel-Sachs
author: "Nome do Autor"
reviewer: "Alice L. Satomi"
published_date: "2026-09-02"
modified_date: "2026-09-02"
images:
  - file: "media/idiofones/nome-do-instrumento/foto.jpg"
    caption: "Legenda da imagem"
    rights: "Créditos da imagem (opcional)"
audio_video_links:
  - title: "Demonstração sonora"
    url: "https://www.youtube.com/watch?v=..."
references:
  - "SOBRENOME, Nome. Ano. Título da obra. Local: Editora."
related_instruments:
  - slug: "reco-reco"
    title: "Reco-reco"
    family: "idiofones"
    relation: "Similar / Variante"
---

# Nome do Instrumento

> Resumo contextual ou citação organológica.

Texto descritivo com contexto sociocultural, materiais, execução e distribuição geográfica.
Links internos para outros instrumentos devem usar o padrão `[Nome](/instrumentos/slug)`.

### Referências

SOBRENOME, Nome. Ano. Título da obra. Local: Editora.
```

### 3. Mídias
- Salvar imagens em `web/public/media/<familia>/<slug>/`.
- Formatos aceitos: JPG, PNG, WebP.

### 4. Validação e Envio
```bash
# 1. Validação estática de integridade
python3 scripts/validate_contribution.py

# 2. Testes e build local
npm --prefix web test
npm --prefix web run build

# 3. Commit e Pull Request
git checkout -b add-instrumento-<slug>
git add web/src/content/instruments/ web/public/media/
git commit -m "feat(acervo): adiciona verbete <slug>"
git push origin add-instrumento-<slug>
```

---

## Estrutura do Repositório

```text
├── web/                           # Aplicação web Astro
│   ├── src/
│   │   ├── content/instruments/   # Verbetes em Markdown (fonte da verdade)
│   │   ├── components/            # Componentes de interface
│   │   ├── layouts/               # Layouts base
│   │   └── pages/                 # Rotas estáticas
│   ├── public/
│   │   ├── media/                 # Acervo de imagens
│   │   └── pagefind/              # Índices de busca
│   └── tests/                     # Testes de conteúdo e componentes
├── scripts/                       # Scripts de extração, espelhamento e validação
├── tests/                         # Testes automatizados Python (pytest)
└── docs/                          # Documentação e especificações
```

---

## Créditos Institucionais

- **Coordenação Científica**: Profª. Drª. Alice Lumi Satomi
- **Laboratório**: LABEET – Laboratório de Estudos Etnomusicológicos
- **Unidade**: CCTA – Centro de Comunicação, Turismo e Artes
- **Instituição**: UFPB – Universidade Federal da Paraíba
- **Projetos**: PDMCP & Brazil Instrumentarium
