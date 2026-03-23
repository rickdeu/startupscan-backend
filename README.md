# StartupScan - Plataforma Completa para Avaliacao de Startups com IA

## 1) Resumo executivo

O StartupScan e uma plataforma full-stack para analise inteligente de startups, combinando:

- entrada multimodal (texto, documento, audio, video, YouTube),
- avaliacao com IA (modelo local e GPT),
- relatorio tecnico automatizado,
- geracao de video explicativo para investidor,
- geracao de pitch deck PDF visual em formato de slides,
- dashboards executivos para operacao e decisao de investimento.

Esta documentacao foi escrita para ser referencia tecnica e operacional do projeto.

---

## 2) Objetivos do sistema

### 2.1 Objetivo de negocio
Reduzir tempo de analise de oportunidades de startup e padronizar a qualidade de feedback para:

- empreendedores,
- analistas,
- aceleradoras,
- investidores.

### 2.2 Objetivo tecnico
Entregar pipeline robusto e escalavel para:

1. receber dados de pitch em multiplos formatos;
2. transformar entradas em features estruturadas;
3. executar avaliacao com explicabilidade;
4. gerar artefatos de comunicacao (PDF e video) para apresentacao.

---

## 3) Escopo funcional detalhado

### 3.1 Submissao multimodal de pitch

Entradas aceitas:

- Texto livre.
- Documento: `.txt`, `.md`, `.csv`, `.pdf`, `.docx`.
- Audio (upload ou gravacao in-browser).
- Video (upload ou gravacao in-browser).
- Link YouTube opcional.
- Dados financeiros:
  - receita,
  - crescimento,
  - margem de lucro.

### 3.2 Avaliacao de startup com IA

Motores:

- `local`: modelo treinado no repositorio.
- `gpt`: analise com API OpenAI quando disponivel.
- fallback automatico para local em caso de falha externa.

Saidas principais:

- score final (0-10),
- resumo executivo,
- pontos fortes,
- pontos fracos,
- recomendacoes,
- categorias de avaliacao.

Categorias:

- Clareza da proposta
- Proposta de valor
- Inovacao
- Viabilidade
- Escalabilidade
- Mercado-alvo
- Equipe
- Sustentabilidade

### 3.3 Relatorio tecnico em PDF

Para cada analise, o sistema pode gerar um PDF com:

- dados submetidos,
- score e categorias,
- interpretacao do resultado,
- recomendacoes praticas.

### 3.4 Video explicativo com IA

A partir do resultado da analise, e possivel gerar video de apresentacao em:

- `auto` (D-ID + fallback local),
- `did_only`,
- `local_only`.

Regras atuais:

- duracao entre 1 e 3 minutos,
- conclusao obrigatoria ao final,
- barra de progresso por fases,
- erros detalhados por cenario (D-ID/local).

### 3.5 Pitch deck PDF visual (slides)

Geracao de pitch para investidores em formato visual:

- 1 pagina = 1 slide,
- capa executiva,
- narrativa estruturada,
- conclusao final,
- design dinamico.

Modos de design:

1. **Design automatico por contexto** (recomendado)
2. **Design premium manual** (template escolhido pelo usuario)

Templates premium suportados:

- Orbit
- Grid
- Wave
- Diagonal
- Aurora
- Ribbon

### 3.6 Gestao de modelos

Painel de modelos com:

- importacao de dataset externo,
- treino e retreino,
- ativacao de modelo,
- edicao de metadados,
- remocao de modelos,
- monitoramento de progresso realtime.

---

## 4) Arquitetura tecnica

### 4.1 Stack

- Backend: Django + Django REST Framework
- IA e dados: scikit-learn, pandas, numpy
- Integracao LLM: OpenAI SDK
- Video/audio: moviepy, edge-tts, gTTS, D-ID API
- Documentos: reportlab, pypdf, python-docx
- Frontend: Django Templates + Bootstrap + JS custom + Chart.js
- Banco: SQLite (dev) e PostgreSQL (compatibilidade)
- Exposicao externa: cloudflared tunnel

### 4.2 Arquitetura de componentes

1. **Camada de entrada**
   - formularios web e endpoint API.
2. **Camada de processamento**
   - extracao multimodal e normalizacao.
3. **Camada de inferencia**
   - pontuacao local/GPT + geracao de relatorio.
4. **Camada de apresentacao**
   - dashboards, resultado detalhado, exportacoes.
5. **Camada de saida**
   - PDF tecnico, pitch deck PDF, video IA.

---

## 5) Estrutura do repositorio

```bash
backend/
startupscan_api/
  services/
    model_registry.py
    model_training.py
    pitch_builder.py
    pitch_input.py
    pitch_video.py
    report_export.py
  templates/analyzer/
    base.html
    dashboard.html
    idea_pitch_detail.html
    idea_pitch_form.html
    investor_dashboard.html
    model_management.html
    pitch_form.html
    result.html
  views.py
  models.py
docs/
  assets/
  generate_engineering_pdf.py
  generate_engineering_docx.py
  Documentacao_Engenharia_Software.pdf
  Documentacao_Engenharia_Software.docx
README.md
requirements.txt
```

---

## 6) Modelos de dados (visao funcional)

### 6.1 PitchAnalysis
Armazena avaliacao principal de startup:

- identificacao da startup,
- dados financeiros,
- arquivos multimodais,
- score de sucesso,
- relatorio estruturado,
- metadados de jobs (video/pitch/exportacao).

### 6.2 IdeaPitchSubmission
Armazena ideia de negocio para fluxo de pitch:

- dados de problema/solucao/mercado/modelo,
- status de geracao,
- payload gerado,
- timestamp de criacao e atualizacao.

---

## 7) Fluxos de negocio

### 7.1 Fluxo de avaliacao

1. Usuario submete pitch multimodal.
2. Backend extrai e consolida texto/contexto.
3. Pipeline gera features e chama motor IA.
4. Sistema salva `PitchAnalysis`.
5. Tela de resultado apresenta score e relatorio.

### 7.2 Fluxo de video IA

1. Usuario seleciona modo de video.
2. Backend cria job assincromo.
3. Frontend consulta endpoint de progresso.
4. Ao concluir, video e persistido na analise.

### 7.3 Fluxo de pitch deck

1. Usuario inicia geracao de pitch PDF.
2. Escolhe design automatico ou premium manual.
3. `pitch_builder` monta slides visuais.
4. Sistema exporta PDF pronto para apresentacao.

---

## 8) Endpoints e paginas principais

- `GET /` - dashboard principal
- `GET /analyze/form/` - formulario de avaliacao
- `POST /analyze/form/` - submissao do pitch
- `GET /results/<analysis_id>/` - pagina de resultado
- `GET /results/<analysis_id>/pdf/` - relatorio tecnico PDF
- `GET /results/<analysis_id>/pitch/pdf/` - pitch deck PDF
- `POST /results/<analysis_id>/video/generate/` - iniciar video IA
- `GET /results/<analysis_id>/video/progress/<job_id>/` - progresso video
- `GET /models/` - gestao de modelos
- `GET /investors/` - dashboard investidor
- `GET /pitch/builder/` - formulario de ideia

---

## 9) Variaveis de ambiente

Principais variaveis:

- `OPENAI_API_KEY` - habilita recursos GPT.
- `OPENAI_MODEL` - modelo OpenAI (ex: `gpt-4.1-mini`).
- `DID_API_KEY` - habilita modo realista via D-ID.
- `DID_API_BASE_URL` - endpoint base da API D-ID.
- `DID_VOICE_ID` - voz utilizada no D-ID.
- `EDGE_TTS_VOICE_PT_AO` - voz TTS preferencial.

Observacao: sem essas chaves, o sistema continua operando com fallbacks locais quando aplicavel.

---

## 10) Setup e execucao local

### 10.1 Instalar dependencias
```bash
python3 -m pip install -r requirements.txt
```

### 10.2 Migrar banco
```bash
python3 manage.py migrate
```

### 10.3 Treino inicial (opcional)
```bash
python3 manage.py train_model --model-output ai_models/pitch_model.pkl
```

### 10.4 Subir servidor
```bash
python3 manage.py runserver 0.0.0.0:8000
```

---

## 10.5) Deploy gratuito com CI/CD (Render + GitHub Actions)

Foi preparado deploy continuo para ambiente gratuito da Render:

- blueprint: `render.yaml`
- workflow: `.github/workflows/deploy-render-main.yml`
- comando web: `Procfile`

### Fluxo

1. Crie um serviço Web na Render a partir deste repositório.
2. Copie o **Deploy Hook URL** do serviço.
3. No GitHub, configure os secrets do repositório:
   - `RENDER_DEPLOY_HOOK_URL` (obrigatório)
   - `RENDER_HEALTHCHECK_URL` (opcional, ex.: `https://<app>.onrender.com/login/`)
4. Ao fazer merge/push na branch `main`, a action dispara deploy automaticamente.

Observações:

- Para recursos GPT/D-ID em produção, configure também na Render:
  - `OPENAI_API_KEY`
  - `DID_API_KEY`
- Se usar PostgreSQL gerenciado, configure `DATABASE_URL`.

---

## 11) Operacao e monitoramento

- Jobs assincromos de treino e video usam estado em cache.
- Frontend usa polling para progresso em tempo real.
- Erros tecnicos sao normalizados para mensagens operacionais.
- Logs de backend ajudam no diagnostico de pipelines multimodais e renderizacao.

---

## 12) Seguranca e resiliencia

- validacao de tipos de ficheiro em uploads,
- protecao CSRF no fluxo web,
- controle de acesso por usuario em views sensiveis,
- tratamento de excecoes com fallback seguro,
- segregacao de cenarios de erro (D-ID vs local) para debug confiavel.

---

## 13) Troubleshooting rapido

### 13.1 Overlay de envio nao desaparece
- Ja corrigido via reset global no `base.html`.
- Se persistir, limpar cache do navegador (`Ctrl+F5`).

### 13.2 Video D-ID falha
- Verificar `DID_API_KEY`, creditos e URL HTTPS de source image.
- Testar modo `local_only` para validar fluxo sem dependencia externa.

### 13.3 PDF nao gera
- Confirmar `reportlab` instalado.
- Verificar permissao de escrita em `MEDIA_ROOT`.

### 13.4 GPT indisponivel
- Confirmar `OPENAI_API_KEY`.
- Sistema deve cair para fallback local automaticamente.

---

## 14) Qualidade, testes e validacao

Comandos principais:

```bash
python3 manage.py check
python3 manage.py test
```

Checklist funcional recomendado:

- submissao multimodal completa,
- score e relatorio com categorias,
- geracao de video nos 3 modos,
- progresso realtime de video/treino,
- pitch PDF com design automatico e premium manual,
- download de relatorio tecnico.

---

## 15) Documentacao tecnica (PDF e DOCX)

Gerar PDF:

```bash
python3 docs/generate_engineering_pdf.py
```

Gerar DOCX:

```bash
python3 docs/generate_engineering_docx.py
```

Arquivos gerados:

- `docs/Documentacao_Engenharia_Software.pdf`
- `docs/Documentacao_Engenharia_Software.docx`

---

## 16) Publicacao no Discord (operacao padrao)

A rotina de entrega da documentacao inclui envio ao webhook do projeto:

- PDF tecnico atualizado
- DOCX tecnico atualizado

Isto garante distribuicao imediata das alteracoes para stakeholders.
