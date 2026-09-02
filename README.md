# Brazil Instrumentarium (LABEET / UFPB)

> Acervo digital e catálogo etnomusicológico dos instrumentos musicais da diversidade brasileira, desenvolvido pelo **Laboratório de Estudos Etnomusicológicos (LABEET / CCTA / UFPB)** sob coordenação da **Profª. Drª. Alice Lumi Satomi**.

O portal reúne mais de 165 verbetes com classificação organológica Hornbostel-Sachs (MIMO), registros iconográficos, transcrições, fonografia e remissões tipológicas.

---

## 🚀 Como Executar Localmente

### Pré-requisitos
- **Node.js** 20+
- **Python** 3.10+

### Instalação e Execução

```bash
# Instalar dependências da aplicação web
cd web && npm install

# Iniciar servidor de desenvolvimento (http://localhost:4321)
npm run dev

# Compilar para produção e gerar índices de busca Pagefind
npm run build

# Executar suíte de testes
npm test
```

Para executar os testes dos scripts Python:
```bash
# Na raiz do repositório
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

---

## 🪕 Como Contribuir com Instrumentos

Novos instrumentos ou revisões de verbetes são bem-vindos! O catálogo é baseado em arquivos Markdown com metadados YAML estruturados.

### 1. Identifique a Família Organológica
Os verbetes ficam organizados em `web/src/content/instruments/<familia>/`:
- `aerofones/`: Instrumentos de sopro (flautas, trombetas, apitos, clarinetes).
- `cordofones/`: Instrumentos de corda (violas, rabecas, berimbaus, arcos).
- `idiofones/`: O próprio corpo do instrumento produz o som (chocalhos, maracás, reco-recos, sinos).
- `membranofones/`: Membrana tensionada vibrante (tambores, caixas, zabumbas, cuícas).

### 2. Crie o Arquivo do Verbete
Crie o arquivo `web/src/content/instruments/<familia>/<slug-do-instrumento>.md` usando o template abaixo:

```yaml
---
title: "Nome do Instrumento"
slug: "nome-do-instrumento"
family: "idiofones" # aerofones | cordofones | idiofones | membranofones
subtitle: "Subtítulo ou nome alternativo (opcional)"
description: "Descrição concisa e classificação organológica (Hornbostel-Sachs)."
mimo_code: "1.1.2.1.1" # Código MIMO / Hornbostel-Sachs (opcional)
author: "Nome do Pesquisador / Autor"
reviewer: "Alice L. Satomi"
published_date: "2026-09-02"
modified_date: "2026-09-02"
images:
  - file: "media/idiofones/nome-do-instrumento/foto_01.jpg"
    caption: "Legenda descritiva da imagem"
    rights: "Créditos da imagem / Acervo (opcional)"
audio_video_links:
  - title: "Demonstração sonora / registro em campo"
    url: "https://www.youtube.com/watch?v=..."
references:
  - "SOBRENOME, Nome. Ano. Título do Livro ou Artigo. Local: Editora."
related_instruments:
  - slug: "reco-reco"
    title: "Reco-reco"
    family: "idiofones"
    relation: "Similar / Variante" # Similar / Variante | Mesmo tipo | Remissão | Contexto / Naipe | Homônimo
---

# Nome do Instrumento

> Resumo contextual ou citação organológica em destaque.

Texto descritivo do instrumento, contexto sociocultural, materiais utilizados, forma de execução e ocorrência geográfica.

Se fizer menção a outro instrumento catalogado, use links internos: `[Reco-reco](/instrumentos/reco-reco)`.

### Referências

SOBRENOME, Nome. Ano. Título da obra. Local: Editora.
```

### 3. Adicione Imagens e Mídias
- Coloque os arquivos de imagem em `web/public/media/<familia>/<slug-do-instrumento>/`.
- Prefira formatos otimizados (`.jpg`, `.jpeg`, `.png`, `.webp`) com boa resolução.

### 4. Conecte Referências Cruzadas
- No campo `related_instruments` do frontmatter, indique instrumentos correlatos, variantes ou que toquem no mesmo conjunto/gênero.
- No corpo do texto, adicione links markdown direcionando para `/instrumentos/<slug-alvo>`.

### 5. Valide e Submeta
```bash
# 1. Valide a integridade do verbete e mídias
python3 scripts/validate_contribution.py

# 2. Verifique os testes e o build
npm --prefix web test
npm --prefix web run build

# 3. Crie um branch e abra um Pull Request
git checkout -b add-instrumento-nome
git add web/src/content/instruments/ web/public/media/
git commit -m "feat(acervo): adiciona verbete do instrumento <Nome>"
git push origin add-instrumento-nome
```

---

## 📂 Estrutura do Repositório

```text
├── web/                           # Aplicação web em Astro
│   ├── src/
│   │   ├── content/instruments/   # Fonte de verdade dos 165+ verbetes Markdown
│   │   │   ├── aerofones/
│   │   │   ├── cordofones/
│   │   │   ├── idiofones/
│   │   │   └── membranofones/
│   │   ├── components/            # Componentes da interface (busca, cards, áudio, citação)
│   │   ├── layouts/               # Layout base com CSP e acessibilidade
│   │   └── pages/                 # Rotas estáticas (/instrumentos, /familia, /sobre)
│   ├── public/
│   │   ├── media/                 # Fotografias e registros visuais dos instrumentos
│   │   └── pagefind/              # Índice estático de busca full-text
│   └── tests/                     # Testes de integridade de conteúdo e componentes
├── scripts/                       # Scripts Python de espelhamento, extração e validação
├── tests/                         # Testes automatizados da pipeline Python (pytest)
└── docs/                          # Especificações técnicas e planos de preservação
```

---

## 🏛️ Créditos e Apoio Institucional

- **Coordenação Científica**: Profª. Drª. Alice Lumi Satomi
- **Laboratório**: LABEET – Laboratório de Estudos Etnomusicológicos
- **Unidade**: CCTA – Centro de Comunicação, Turismo e Artes
- **Instituição**: UFPB – Universidade Federal da Paraíba
- **Projetos Associados**: PDMCP (Pesquisa e Documentação de Música e Cultura Popular) & Brazil Instrumentarium
