# StartupScan - Plataforma Multimodal para Pitch Automatizado de Startups

Plataforma web para avaliacao automatica de pitches com **entrada multimodal** (texto, documento, audio, video e link YouTube), geracao de **score de sucesso (0-10)**, **feedback por categoria**, dashboard interativo e **exportacao de relatorio em PDF**.

## Objetivo

Apoiar empreendedores na validacao de ideias com um fluxo rapido:

1. Submeter pitch (texto/doc/audio/video/youtube)
2. Processar com IA (motor local ou GPT com fallback)
3. Gerar score + recomendacoes automaticas
4. Exibir progresso no dashboard
5. Baixar relatorio final em PDF

## Funcionalidades principais

### 1) Submissao multimodal
- Texto direto no formulario
- Upload de documento: `.txt`, `.md`, `.csv`, `.pdf`, `.docx`
- Audio por upload ou gravacao no navegador (MediaRecorder)
- Video por upload ou gravacao no navegador (MediaRecorder)
- Link do YouTube opcional para contexto do pitch

### 2) Analise com IA
- Escolha de motor:
  - **local** (modelo treinado no projeto)
  - **gpt** (quando `OPENAI_API_KEY` estiver configurada)
- Fallback automatico para modelo local quando GPT indisponivel
- Score final de sucesso em escala 0-10
- Avaliacao por categoria (0-10):
  - Clareza da ideia
  - Proposta de valor
  - Inovacao
  - Viabilidade tecnica/financeira
  - Escalabilidade
  - Mercado-alvo
  - Equipe fundadora
  - Sustentabilidade

### 3) Relatorio automatico
- Resumo executivo
- Pontos fortes
- Pontos a melhorar
- Recomendacoes de proxima etapa
- Bloco investidor (tese, prontidao, uso de capital, mitigacao)
- Download do relatorio em PDF por analise

### 4) Dashboard interativo
- Historico de pitches enviados
- Evolucao de score
- Distribuicao de potencial
- Tracao financeira
- Comparacao por sector (benchmark)

## Stack tecnica

- **Backend:** Django + Django REST Framework
- **ML:** scikit-learn, pandas, numpy
- **Documentos e PDF:** pypdf, python-docx, reportlab
- **Visualizacao:** Chart.js, matplotlib
- **Persistencia:** SQLite (dev), compatibilidade com PostgreSQL

## Estrutura de pastas (resumo)

```bash
backend/
startupscan_api/
  services/
    pitch_input.py         # extracao de texto de documentos e merge multimodal
    report_export.py       # geracao de PDF da analise
  templates/analyzer/
    pitch_form.html        # formulario multimodal + gravacao browser
    dashboard.html         # analytics e comparacao por sector
    result.html            # relatorio e download PDF
docs/
  generate_engineering_pdf.py
  Documentacao_Engenharia_Software.pdf
```

## Como executar localmente

1. Instalar dependencias:

```bash
python3 -m pip install -r requirements.txt
```

2. Aplicar migracoes:

```bash
python3 manage.py migrate
```

3. (Opcional) Treinar modelo:

```bash
python3 manage.py train_model --model-output ai_models/pitch_model.pkl
```

4. Subir servidor:

```bash
python3 manage.py runserver 0.0.0.0:8000
```

## Endpoints importantes

- `GET /analyze/form/` - formulario multimodal
- `POST /analyze/form/` - submissao de pitch
- `GET /results/<analysis_id>/` - resultado da analise
- `GET /results/<analysis_id>/pdf/` - download do relatorio PDF
- `GET /` - dashboard do usuario
- `GET /investor/dashboard/` - dashboard investidor
- `POST /analyze/` - API de analise

## Gerar documentacao PDF tecnica

```bash
python3 docs/generate_engineering_pdf.py
```

Arquivo gerado:

`docs/Documentacao_Engenharia_Software.pdf`

## Qualidade e validacao

Comandos de verificacao:

```bash
python3 manage.py check
python3 manage.py test
```

Tambem e recomendado executar testes funcionais de:
- submissao com documento
- analise com score e categorias
- download de PDF
- leitura de benchmark por sector no dashboard
