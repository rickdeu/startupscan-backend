# StartupScan - Plataforma Inteligente para Avaliação de Startups

Plataforma web multimodal para avaliar startups com IA, gerar relatórios técnicos, criar vídeos explicativos e produzir pitch decks em PDF com design automático por contexto ou design premium manual.

## Visão geral

O StartupScan foi desenhado para apoiar empreendedores, aceleradoras e investidores no ciclo completo:

1. Receber pitch multimodal (texto, documento, áudio, vídeo e YouTube).
2. Gerar análise com motor local ou GPT (com fallback automático).
3. Exibir score e categorias de desempenho com recomendações acionáveis.
4. Produzir relatório técnico em PDF.
5. Gerar vídeo de apresentação (D-ID/local/híbrido) com progresso em tempo real.
6. Criar pitch deck em PDF (estilo slides) com visual adaptado ao contexto da startup.

---

## Funcionalidades principais

### 1) Submissão multimodal de pitch
- Campo de texto livre.
- Upload de ficheiros: `.txt`, `.md`, `.csv`, `.pdf`, `.docx`.
- Áudio via upload ou gravação no navegador.
- Vídeo via upload ou gravação no navegador.
- URL de YouTube opcional para contexto adicional.

### 2) Avaliação inteligente com IA
- Seleção de motor:
  - **local** (modelo treinado no projeto)
  - **gpt** (se `OPENAI_API_KEY` estiver configurada)
- Fallback automático para o motor local.
- Score final de 0 a 10.
- Categorias de análise (0-10):
  - Clareza
  - Proposta de valor
  - Inovação
  - Viabilidade
  - Escalabilidade
  - Mercado-alvo
  - Equipa
  - Sustentabilidade

### 3) Gestão de modelos de ML
- Importar dataset externo.
- Treinar novo modelo.
- Retreinar modelo existente.
- Definir modelo ativo.
- Editar metadados.
- Excluir modelo.
- Progresso em tempo real por job de treino.

### 4) Vídeo explicativo da startup
- Geração assíncrona com barra de progresso por fases.
- Modos disponíveis:
  - **D-ID + fallback local** (recomendado)
  - **Apenas D-ID**
  - **Apenas local**
- Duração configurada no pipeline: **mínimo 1 minuto e máximo 3 minutos**.
- Encerramento obrigatório com conclusão explícita no final.
- Erros detalhados separados por cenário (D-ID e local).

### 5) Pitch PDF em formato de apresentação (slides)
- Geração de PDF tipo deck (1 página = 1 slide).
- Capa visual, seções de conteúdo e conclusão.
- Modo de design:
  - **Design automático por contexto** (default)
  - **Design premium manual** (template escolhido pelo utilizador)
- Templates premium suportados:
  - Orbit
  - Grid
  - Wave
  - Diagonal
  - Aurora
  - Ribbon
- Variação visual por assinatura única do pitch.

### 6) Relatórios e dashboards
- Relatório técnico de análise em PDF.
- Dashboard operacional do utilizador.
- Dashboard orientado a investidor.
- Histórico de análises, score médio, distribuição por potencial e indicadores financeiros.

---

## Stack técnica

- **Backend:** Django + Django REST Framework
- **IA/Modelagem:** scikit-learn, pandas, numpy
- **NLP/GPT:** OpenAI SDK (quando configurado)
- **Vídeo/áudio:** moviepy, edge-tts, gTTS, integração D-ID
- **PDF/Documentos:** reportlab, pypdf, python-docx
- **Frontend:** Django Templates, Bootstrap, Chart.js, JS custom
- **Persistência:** SQLite (dev), compatível com PostgreSQL

---

## Estrutura resumida

```bash
backend/
startupscan_api/
  services/
    pitch_input.py          # extração e merge multimodal
    report_export.py        # relatório técnico PDF
    pitch_builder.py        # geração de pitch + pitch deck PDF visual
    pitch_video.py          # geração de vídeo IA (D-ID/local)
    model_registry.py       # gestão de modelos
  templates/analyzer/
    pitch_form.html
    result.html
    dashboard.html
    investor_dashboard.html
    model_management.html
docs/
  generate_engineering_pdf.py
  Documentacao_Engenharia_Software.pdf
README.md
```

---

## Execução local

### 1) Instalar dependências
```bash
python3 -m pip install -r requirements.txt
```

### 2) Migrar base de dados
```bash
python3 manage.py migrate
```

### 3) (Opcional) Treinar modelo local inicial
```bash
python3 manage.py train_model --model-output ai_models/pitch_model.pkl
```

### 4) Subir aplicação
```bash
python3 manage.py runserver 0.0.0.0:8000
```

---

## Endpoints e páginas principais

- `GET /` - Dashboard principal
- `GET /analyze/form/` - Formulário de avaliação multimodal
- `POST /analyze/form/` - Submissão e avaliação
- `GET /results/<analysis_id>/` - Resultado da análise
- `GET /results/<analysis_id>/pdf/` - Relatório PDF da análise
- `GET /results/<analysis_id>/pitch/pdf/` - Pitch deck PDF (slides)
- `POST /results/<analysis_id>/video/generate/` - Iniciar geração de vídeo
- `GET /results/<analysis_id>/video/progress/<job_id>/` - Progresso do vídeo
- `GET /models/` - Gestão de modelos
- `GET /investors/` - Dashboard de investidores
- `GET /pitch/builder/` - Formulário de ideia para pitch

---

## Geração de documentação técnica

### Gerar PDF de engenharia
```bash
python3 docs/generate_engineering_pdf.py
```

Arquivo gerado:
- `docs/Documentacao_Engenharia_Software.pdf`

### Atualizar documentação completa (README + PDF + envio webhook)
Fluxo recomendado:
1. Atualizar `README.md`.
2. Executar `python3 docs/generate_engineering_pdf.py`.
3. Enviar PDF para o webhook do Discord com `curl`.

---

## Validação e qualidade

Comandos úteis:

```bash
python3 manage.py check
python3 manage.py test
```

Teste funcional recomendado:
- Submissão multimodal completa.
- Geração de score + categorias + recomendações.
- Geração de vídeo nos 3 modos (auto, did_only, local_only).
- Exportação de pitch PDF nos 2 modos de design.
- Download de relatório técnico PDF.
