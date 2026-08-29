# Especificação de Design: Resgate, Preservação e Estruturação do Acervo LABEET / Brazil Instrumentarium

**Data:** 2026-08-29  
**Status:** Em Revisão  
**Escopo:** Sub-projeto 1 — Preservação Integral e Extração Estruturada  

---

## 1. Contexto e Motivação

O **LABEET** (Laboratório de Estudos Etnomusicológicos da Universidade Federal da Paraíba - UFPB / CCTA) hospeda o acervo digital **Brazil Instrumentarium (Brazinst)**, primeiro acervo digital dedicado exclusivamente a instrumentos musicais brasileiros, fundamentado no sistema de classificação organológica Hornbostel-Sachs (MIMO Consortium) e coordenado pela Profa. Dra. Alice Satomi.

Atualmente, o site está hospedado em um endereço IP direto sem nome de domínio (`http://150.165.254.38/labeet`), executando uma instalação legada de **Plone CMS** (atrás de Nginx e Varnish). Não há credenciais de acesso direto ao servidor (SSH/banco de dados) disponíveis.

Com a saída iminente da pesquisadora da universidade e a fragilidade de servidores legados mantidos em IP puro, existe **risco real de desativação súbita da infraestrutura**, o que acarretaria a perda irreversível de anos de pesquisa etnomusicológica.

### Objetivos do Sub-projeto 1
1. **Preservação Integral Local (Risco Zero):** Criar um espelho bruto navegável 100% offline de todo o site do LABEET (páginas, folhas de estilo, imagens originais e publicações em PDF).
2. **Extração Estruturada do Brazil Instrumentarium:** Transformar os verbetes de instrumentos em arquivos **Markdown** com metadados estruturados (**YAML frontmatter**) e compilar um catálogo geral em **JSON** acompanhado de suas imagens organizadas.
3. **Resiliência a Falhas (Checkpoint/Resume):** Permitir que qualquer etapa do download seja interrompida (por queda de rede, timeout do servidor ou cancelamento manual) e continue exatamente de onde parou, sem perda de dados nem downloads duplicados.
4. **Transparência e Observabilidade:** Exibir logs ricos em tempo real informando exatamente onde cada arquivo está sendo salvo, o progresso percentual e a contagem de itens.
5. **Preservação Pública Perpétua:** Submeter as páginas descobertas à Wayback Machine (Internet Archive).
6. **Auditoria e Validação:** Gerar um relatório detalhado de inventário e integridade atestando que nenhum instrumento ou mídia foi omitido.

---

## 2. Estrutura de Diretórios

O projeto será mantido no repositório local `/Users/gregoriomelo/dev/labeet` com a seguinte organização:

```text
/Users/gregoriomelo/dev/labeet/
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-08-29-labeet-preservation-subproject1-design.md
├── scripts/
│   ├── common.py                # Utilitários compartilhados (HTTP, logging, checkpoint)
│   ├── mirror.py                 # Crawler e espelhador bruto integral do site
│   ├── extract_brazinst.py       # Extrator semântico para Markdown e JSON
│   ├── archive_wayback.py        # Submissão das URLs ao Internet Archive
│   └── validate.py               # Auditoria, contagem e integridade
├── backup_full/                  # ESPELHO BRUTO DO SITE COMPLETO (100% offline)
│   ├── state.json                # Manifesto de checkpoint com status de cada URL
│   ├── index.html                # Entrada para navegação local offline
│   ├── labeet/                   # Arquivos HTML espelhados mantendo hierarquia original
│   ├── portal_css/               # Folhas de estilo do tema Plone
│   ├── portal_javascripts/       # Scripts necessários para layout
│   └── media/                    # Imagens e anexos em resolução original
└── content_brazinst/             # DADOS LIMPOS DO BRAZIL INSTRUMENTARIUM
    ├── state_extraction.json     # Checkpoint da extração semântica
    ├── instruments/              # Verbetes individuais em Markdown por família
    │   ├── idiofones/            # ex: agogo.md, caxixi.md, etc.
    │   ├── membranofones/        # ex: atabaque.md, surdo.md, etc.
    │   ├── cordofones/           # ex: berimbau.md, cavaquinho.md, etc.
    │   └── aerofones/            # ex: pifano.md, maraca.md, etc.
    ├── media/                    # Fotos organizadas por instrumento
    │   ├── idiofones/
    │   ├── membranofones/
    │   ├── cordofones/
    │   └── aerofones/
    ├── brazinst_catalog.json     # Catálogo consolidado em JSON
    └── inventory_report.md       # Relatório final de auditoria
```

---

## 3. Arquitetura de Resiliência: Checkpoint, Resume e Tolerância a Falhas

Como o servidor da UFPB é antigo e pode oscilar, o mecanismo de recuperação é requisito central de projeto:

### 3.1. Manifesto de Estado (`state.json`)
Cada etapa mantém um manifesto de estado em disco com o seguinte formato:
```json
{
  "last_updated": "2026-08-29T20:45:00Z",
  "queue": [],
  "visited": {
    "http://150.165.254.38/labeet/contents/menu/acervos/apresentacao": {
      "status": "completed",
      "http_code": 200,
      "local_path": "backup_full/labeet/contents/menu/acervos/apresentacao/index.html",
      "content_type": "text/html;charset=utf-8",
      "bytes": 26653,
      "attempts": 1,
      "retrieved_at": "2026-08-29T20:45:00Z"
    }
  },
  "failed": {}
}
```

### 3.2. Regras de Resume e Idempotência
1. **Verificação de existência e integridade:** Antes de disparar qualquer requisição de rede, o script verifica se a URL já está registrada com `status: "completed"` e se o arquivo local correspondente existe com tamanho $> 0$ bytes. Se sim, ignora e avança para a próxima.
2. **Escrita Atômica:** Todo download é gravado primeiramente em um arquivo temporário (`.tmp`). Somente após a conclusão com sucesso da transferência o arquivo é renomeado para o caminho definitivo. Isso impede arquivos corrompidos ou incompletos por encerramento abrupto.
3. **Tentativas com Recuo Exponencial (Backoff):**
   - Tentativa 1: Imediata.
   - Tentativa 2: Espera 2 segundos.
   - Tentativa 3: Espera 5 segundos.
   - Se falhar 3 vezes, a URL é marcada no bloco `failed` com o erro ocorrido, permitindo que a execução continue com as demais páginas sem travar todo o processo.
4. **Feedback de Continuação no Terminal:**
   Ao ser iniciado, o script emite mensagens claras:
   ```text
   [CHECKPOINT] Carregando estado anterior de backup_full/state.json...
   [CHECKPOINT] 142 URLs já baixadas com sucesso. 38 pendentes na fila. Continuando...
   ```

---

## 4. Componentes do Pipeline

### 4.1. `mirror.py` — Espelhador Bruto do LABEET
* **Fronteira Rígida de Domínio:** Inicia em `http://150.165.254.38/labeet`. Apenas URLs iniciadas com `http://150.165.254.38/labeet` são adicionadas à fila de rastreamento. Links para redes sociais, sites externos ou outros sistemas da UFPB são catalogados, mas não rastreados.
* **Resolução de Imagens no Plone:**
  - O Plone serve imagens em diversas resoluções (ex: `/image.jpg/image_preview`, `/image.jpg/image_large`, `/image.jpg/@@images/hash.jpeg`).
  - O extrator identifica a URL canônica do recurso original para baixar a mídia em resolução máxima.
* **Reescrita de Links para Navegação Offline:**
  - Todas as referências a CSS, JS e imagens nos arquivos HTML são reescritas para caminhos relativos ao diretório local.
  - Ao abrir `backup_full/index.html` em qualquer navegador, todas as páginas funcionam sem conexão.
* **Taxa de Requisição Amigável (Polite Crawling):**
  - Intervalo de 0.2s a 0.5s entre requisições para evitar sobrecarga no servidor.

### 4.2. `extract_brazinst.py` — Extrator Semântico do Brazil Instrumentarium
Opera sobre os dados locais baixados (ou diretamente via HTTP caso o espelho ainda não tenha sido executado), garantindo independência:
1. **Navegação nas 4 Categorias Organológicas:**
   - Idiofones: `/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones`
   - Membranofones: `/labeet/contents/paginas/acervo-brazinst/copy_of_membranofones`
   - Cordofones: `/labeet/contents/paginas/acervo-brazinst/copy_of_cordofones`
   - Aerofones: `/labeet/contents/paginas/acervo-brazinst/copy_of_aerofones`
2. **Extração de Cada Verbete:**
   - Parse do layout NITF do Plone (`class="newsview"`, `h1.documentFirstHeading`, `#parent-fieldname-text`, `#plone-document-byline`).
   - Extração do corpo textual com conversão limpa para Markdown.
   - Extração estruturada de seções isoladas:
     - *Classificação organológica / código MIMO*
     - *Referências bibliográficas*
     - *Fonografia (links de áudio/vídeo)*
     - *Autores e tradutores*
     - *Galeria de fotos (baixadas para `content_brazinst/media/<familia>/<slug>/`)*
3. **Geração de Saídas:**
   - Criação de `content_brazinst/instruments/<familia>/<slug>.md`.
   - Consolidação de todos os dados em `content_brazinst/brazinst_catalog.json`.

### 4.3. `archive_wayback.py` — Submissão para Internet Archive
* Lê todas as URLs catalogadas no `backup_full/state.json`.
* Envia requisições para a API pública `https://web.archive.org/save/<URL>`.
* Salva o mapa de URLs permanentes do Wayback Machine (`https://web.archive.org/web/<timestamp>/<URL>`) no relatório de inventário.

### 4.4. `validate.py` — Auditoria e Inventário
Executa verificações cruzadas e gera `content_brazinst/inventory_report.md`:
* **Completude:** Compara a quantidade de instrumentos listados nas páginas de categorias com os arquivos `.md` gerados.
* **Integridade de Mídias:** Confirma se todas as imagens referenciadas nos metadados YAML dos arquivos Markdown existem no disco e possuem tamanho válido ($> 0$ bytes).
* **Mapeamento de Links Quebrados:** Registra qualquer link no site original que já estava inacessível (erro 404) para referência futura.

---

## 5. Especificação do Esquema de Dados

### 5.1. Esquema YAML Frontmatter dos Instrumentos
Cada arquivo em `content_brazinst/instruments/<familia>/<slug>.md` seguirá este esquema padronizado:

```yaml
---
title: "Nome do Instrumento"
slug: "nome-do-instrumento"
family: "idiofones" # "idiofones" | "membranofones" | "cordofones" | "aerofones"
mimo_code: "111.242" # Quando disponível na tabela organológica
source_url: "http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/..."
author: "Nome do Autor / Bolsista"
reviewer: "Alice L. Satomi"
published_date: "AAAA-MM-DD"
modified_date: "AAAA-MM-DD"
thumbnail: "media/idiofones/nome-do-instrumento/thumb.jpg"
images:
  - file: "media/idiofones/nome-do-instrumento/foto_01.jpg"
    caption: "Legenda da imagem"
    rights: "Créditos ou direitos autorais se informados"
audio_video_links:
  - title: "Descrição do registro sonoro"
    url: "https://www.youtube.com/watch?v=..."
    access_date: "AAAA-MM-DD"
references:
  - "Referência bibliográfica 1 no formato ABNT"
  - "Referência bibliográfica 2"
---

Corpo do verbete em Markdown puro com contextualização histórica, sonora, social e organológica...
```

### 5.2. Esquema do Catálogo JSON (`brazinst_catalog.json`)
```json
{
  "project": "Brazil Instrumentarium",
  "source_laboratory": "LABEET - UFPB",
  "exported_at": "2026-08-29T20:00:00Z",
  "total_instruments": 42,
  "instruments": [
    {
      "id": "agogo",
      "title": "Agogô",
      "family": "idiofones",
      "mimo_code": "111.242",
      "file_path": "instruments/idiofones/agogo.md",
      "thumbnail": "media/idiofones/agogo/agogo_thumb.jpg",
      "media_count": 3,
      "audio_video_count": 2,
      "has_references": true
    }
  ]
}
```

---

## 6. Observabilidade e Mensagens de Progresso no Terminal

Para atender ao requisito de transparência total onde o usuário acompanha em tempo real o que está acontecendo e onde os arquivos estão sendo salvos:

Exemplo de saída emitida pelo console:
```text
[17:50:01] [INÍCIO] Iniciando pipeline de preservação do LABEET...
[17:50:02] [CHECKPOINT] Arquivo de estado carregado: 12 itens já concluídos.
[17:50:03] [FILA: 13/85] Baixando HTML: http://150.165.254.38/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/agogo
           -> Salvo em: backup_full/labeet/contents/paginas/acervo-brazinst/copy_of_idiofones/agogo/index.html (24.2 KB)
[17:50:04] [MÍDIA] Baixando imagem: http://150.165.254.38/.../agogo.jpg/@@images/...
           -> Salvo em: backup_full/media/agogo_01.jpg (340.5 KB)
[17:50:05] [EXTRAÇÃO] Processando verbete 'Agogô' (Idiofones)...
           -> Verbete estruturado: content_brazinst/instruments/idiofones/agogo.md
           -> Imagens vinculadas: 1 imagem salva em content_brazinst/media/idiofones/agogo/
[17:50:06] [PROGRESSO] 13/85 URLs processadas (15.2%). Taxa: 1.2 req/s.
```

---

## 7. Critérios de Sucesso e Validação

O Sub-projeto 1 será considerado concluído com sucesso quando:
1. **Navegabilidade Offline Integral:** Abrir `backup_full/index.html` em um navegador sem internet renderizar o site completo do LABEET com folhas de estilo e imagens.
2. **100% de Extração dos Verbetes:** Todos os instrumentos das 4 famílias organológicas possuírem seu arquivo `.md` correspondente e estarem listados no `brazinst_catalog.json`.
3. **Auditoria de Mídias Aprovada:** O script `validate.py` confirmar zero imagens ausentes e zero referências órfãs.
4. **Resiliência Comprovada:** Interromper a execução (`Ctrl+C`) e executá-la novamente deve continuar sem refazer requisições de arquivos já existentes.
5. **Relatório Gerado:** O arquivo `content_brazinst/inventory_report.md` estiver preenchido com todos os totais e logs do processo.
