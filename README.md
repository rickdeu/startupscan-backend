# StartupScan — Plataforma de Avaliação Inteligente de Startups

StartupScan é uma plataforma web full-stack que automatiza a avaliação de startups usando inteligência artificial. Combina entrada multimodal (texto, documentos, áudio, vídeo), modelos de ML locais e integração com GPT para produzir um score de 0 a 10, um relatório técnico detalhado, um pitch deck visual em PDF e um vídeo explicativo narrado gerado por IA.

O sistema serve empreendedores que querem validar ideias, analistas que avaliam oportunidades em escala, e investidores que precisam de triagem rápida de deals.

---

## Índice

1. [Contexto e propósito](#1-contexto-e-propósito)
2. [Funcionalidades principais](#2-funcionalidades-principais)
3. [Arquitectura técnica](#3-arquitectura-técnica)
4. [Papéis de utilizador](#4-papéis-de-utilizador)
5. [Modelos de dados](#5-modelos-de-dados)
6. [Pré-requisitos](#6-pré-requisitos)
7. [Setup local passo a passo](#7-setup-local-passo-a-passo)
8. [Variáveis de ambiente](#8-variáveis-de-ambiente)
9. [Treino do modelo de IA](#9-treino-do-modelo-de-ia)
10. [Uso da plataforma](#10-uso-da-plataforma)
11. [Referência de endpoints](#11-referência-de-endpoints)
12. [Execução com Docker Compose](#12-execução-com-docker-compose)
13. [Deploy na Render (CI/CD)](#13-deploy-na-render-cicd)
14. [Testes e validação](#14-testes-e-validação)
15. [Troubleshooting](#15-troubleshooting)
16. [Documentação técnica adicional](#16-documentação-técnica-adicional)

---

## 1. Contexto e propósito

### O problema

A avaliação manual de pitches de startups é lenta, subjectiva e não escala. Um analista experiente consegue avaliar alguns pitches por semana; uma aceleradora recebe dezenas por mês. O feedback é inconsistente entre avaliadores e raramente inclui artefactos concretos que o empreendedor possa usar.

### A solução

O StartupScan automatiza o ciclo completo: da submissão do pitch à entrega de artefactos prontos para apresentação.

1. O empreendedor submete o pitch em qualquer formato (texto, PDF, vídeo, áudio ou link YouTube) com dados financeiros básicos.
2. O sistema extrai, normaliza e combina todas as entradas.
3. Um pipeline de ML (scikit-learn + XGBoost) ou GPT gera um score de sucesso com categorias e explicabilidade.
4. São produzidos automaticamente: relatório técnico PDF, pitch deck visual PDF e vídeo narrado por IA.
5. Investidores podem expressar interesse em startups directamente na plataforma.

### Para quem é

| Perfil | O que usa |
|---|---|
| Empreendedor | Submissão de pitch, construtor de ideias, pitch deck PDF |
| Analista | Dashboard, avaliação em lote (CSV), gestão de modelos |
| Investidor | Dashboard de deal flow, conexões com startups |
| Público geral | Navegação de ideias públicas, feedback com estrelas |
| Admin | Gestão de utilizadores, modelos de ML, configuração |

---

## 2. Funcionalidades principais

### Avaliação de startup (core)

- Submissão multimodal: texto livre, `.txt`, `.md`, `.csv`, `.pdf`, `.docx`, áudio, vídeo, link YouTube
- Dados financeiros: receita (AOA), taxa de crescimento, margem de lucro, burn rate
- Score final de 0 a 10 com nível de confiança percentual
- Relatório com 8 categorias: Clareza da Proposta, Proposta de Valor, Inovação, Viabilidade, Escalabilidade, Mercado-Alvo, Equipa, Sustentabilidade
- Pontos fortes, pontos fracos e recomendações práticas
- Fallback automático para modelo local quando GPT não está disponível

### Processamento em lote

- Upload de CSV com múltiplos pitches
- Processamento assíncrono com polling de progresso
- Download de resultados consolidados

### Relatório técnico PDF

Gerado para cada análise:

- Score, confiança e categorias
- Dados financeiros submetidos
- Análise interpretável
- Recomendações práticas
- Metadados do modelo usado

### Pitch deck PDF (slides para investidores)

- 1 página = 1 slide
- Capa executiva, narrativa estruturada, conclusão
- **Design automático por contexto** (recomendado): o sistema escolhe o template com base na indústria e dados
- **Design premium manual**: o utilizador escolhe entre 6 templates — Orbit, Grid, Wave, Diagonal, Aurora, Ribbon

### Vídeo explicativo com IA

Gerado a partir do resultado da análise:

- **Modo `auto`**: tenta D-ID API (apresentador realista) com fallback para vídeo local
- **Modo `did_only`**: apenas D-ID (falha se API indisponível)
- **Modo `local_only`**: moviepy + TTS local (sem dependências externas)
- Duração entre 1 e 3 minutos
- Progresso em tempo real via polling
- Suporte a detecção de género do apresentador (deepface)

### Construtor de ideias (pitch builder)

- Formulário guiado: problema, solução, cliente-alvo, mercado, modelo de negócio, vantagem competitiva, tracção, equipa, financiamento
- Geração automática do pitch narrativo (local ou GPT)
- Exportação como PDF
- Publicação como ideia pública para receber feedback da comunidade

### Conexões investidor-startup

- Investidor expressa interesse numa análise com mensagem
- Empreendedor vê o interesse no hub de conexões
- Ciclo de resposta: `pending → reviewing → connected / rejected`

### Gestão de modelos de ML

- Upload de datasets personalizados (pitches + financeiros)
- Treino e retreino com progresso em tempo real
- Ativação de modelo específico
- Edição de metadados e remoção de modelos
- Importação de datasets externos

---

## 3. Arquitectura técnica

### Stack

| Camada | Tecnologia |
|---|---|
| Framework web | Django 6 + Django REST Framework |
| Frontend | Django Templates + Bootstrap + Chart.js |
| Base de dados | SQLite (dev) / PostgreSQL (prod) |
| Cache e filas | Redis + Celery |
| ML / IA | scikit-learn, XGBoost, pandas, numpy |
| LLM | OpenAI SDK (GPT) |
| Vídeo | moviepy, OpenCV, deepface, D-ID API |
| Áudio / TTS | Whisper, librosa, gTTS, edge-tts |
| PDF | ReportLab, pypdf, python-docx |
| Servidor | Gunicorn + WhiteNoise |
| Deploy | Docker, Render.com, Kubernetes (opcional) |

### Fluxo de dados

```
Utilizador
    │
    ▼
Formulário web / API
    │
    ▼
Extração multimodal (pitch_input.py)
  ├── Texto directo
  ├── PDF / DOCX / CSV / TXT → texto
  ├── Áudio → Whisper → texto
  └── Vídeo / YouTube → áudio → Whisper → texto
    │
    ▼
Feature engineering + dados financeiros
    │
    ▼
Motor de IA
  ├── Modelo local (scikit-learn / XGBoost)
  └── GPT (fallback / alternativo)
    │
    ▼
PitchAnalysis guardado na BD
    │
    ├── Relatório técnico PDF (report_export.py)
    ├── Pitch deck PDF (pitch_builder.py)
    └── Vídeo narrado (pitch_video.py)
```

### Componentes assíncronos

Treino de modelos e geração de vídeo correm como jobs assíncronos. O frontend faz polling dos endpoints de progresso até conclusão.

```
Cliente → POST /model/retrain/ → cria job_id → retorna imediatamente
Cliente → GET /models/training/progress/<job_id>/ → estado do job
                                  (repete até status=completed)
```

---

## 4. Papéis de utilizador

O sistema usa um modelo de controlo de acesso baseado em papéis (RBAC).

| Papel | Registo público | Capacidades |
|---|---|---|
| `admin` | Não (superuser Django) | Tudo, incluindo gestão de utilizadores e modelos |
| `analista` | Sim | Dashboard, avaliação, lote, gestão de modelos |
| `empreendedor` | Sim | Dashboard, submissão de pitch, construtor de ideias, conexões |
| `investidor` | Sim | Dashboard investidor, expressar interesse, hub de conexões |
| `publico_geral` | Sim (default) | Navegar ideias públicas, dar feedback |

Ao registar, o utilizador escolhe o seu papel. Administradores são criados via `createsuperuser` ou pela interface de admin Django em `/admin/`.

---

## 5. Modelos de dados

### PitchAnalysis

Registo central de cada avaliação.

| Campo | Tipo | Descrição |
|---|---|---|
| `user` | FK User (nullable) | Utilizador que submeteu |
| `startup_name` | CharField | Nome da startup |
| `industry` | CharField | Sector (tech, health, finance, education, ecommerce, other) |
| `contact_email` | EmailField | Email de contacto |
| `text` | TextField | Pitch em texto |
| `audio_file` | FileField | Áudio enviado |
| `video_file` | FileField | Vídeo enviado |
| `document_file` | FileField | Documento enviado |
| `presenter_face_image_file` | FileField | Foto do apresentador |
| `youtube_url` | URLField | Link YouTube |
| `revenue` | DecimalField | Receita (AOA) |
| `growth_rate` | FloatField | Taxa de crescimento (%) |
| `profit_margin` | FloatField | Margem de lucro (%) |
| `burn_rate` | DecimalField | Burn rate mensal |
| `success_score` | FloatField | Score final 0–10 |
| `confidence` | FloatField | Confiança da previsão (%) |
| `report` | JSONField | Relatório estruturado completo |
| `status` | CharField | pending / processing / completed / failed |
| `model_version` | CharField | Versão do modelo usado |
| `processing_time` | FloatField | Tempo de processamento (s) |

### UserProfile

Extende o utilizador Django com papel.

| Campo | Tipo | Descrição |
|---|---|---|
| `user` | OneToOneField | Utilizador Django |
| `role` | CharField | Um dos 5 papéis |

### IdeaPitchSubmission

Ideia de negócio no construtor.

| Campo | Tipo | Descrição |
|---|---|---|
| `startup_name` | CharField | Nome |
| `one_liner` | CharField | Pitch de uma frase |
| `problem` | TextField | Problema que resolve |
| `solution` | TextField | Solução proposta |
| `target_customer` | TextField | Cliente-alvo |
| `market_size` | TextField | Tamanho do mercado |
| `business_model` | TextField | Modelo de negócio |
| `competitive_advantage` | TextField | Diferencial competitivo |
| `traction` | TextField | Tracção actual |
| `team` | TextField | Equipa |
| `funding_goal` | CharField | Meta de financiamento |
| `use_of_funds` | TextField | Uso dos fundos |
| `model_source` | CharField | local / gpt |
| `status` | CharField | draft / generated |
| `generated_pitch` | JSONField | Pitch gerado |

### InvestorConnectionInterest

Interesse de um investidor numa startup.

| Campo | Tipo | Descrição |
|---|---|---|
| `analysis` | FK PitchAnalysis | Análise de interesse |
| `investor` | FK User | Investidor |
| `entrepreneur` | FK User (nullable) | Empreendedor destinatário |
| `status` | CharField | pending / reviewing / connected / rejected / withdrawn |
| `investor_message` | TextField | Mensagem do investidor |
| `entrepreneur_reply` | TextField | Resposta do empreendedor |

### IdeaPublicFeedback

Avaliação da comunidade sobre ideias públicas.

| Campo | Tipo | Descrição |
|---|---|---|
| `submission` | FK IdeaPitchSubmission | Ideia avaliada |
| `author` | FK User | Quem avaliou |
| `stars` | IntegerField | 1 a 5 estrelas |
| `endorsed` | BooleanField | Endorsement |
| `comment` | TextField | Comentário |

---

## 6. Pré-requisitos

Antes de começar, garante que tens o seguinte instalado:

- **Python 3.10+** — `python --version`
- **pip** — incluído com Python
- **Git** — para clonar o repositório
- **Redis** (opcional, para Celery) — necessário apenas para jobs assíncronos de treino e vídeo
- **FFmpeg** (opcional) — necessário para geração de vídeo local

Para verificar:

```bash
python --version      # Python 3.10.x ou superior
pip --version
git --version
redis-cli ping        # PONG (se instalado)
ffmpeg -version       # (se instalado)
```

> **Nota:** O sistema funciona sem Redis e FFmpeg em modo básico (avaliação, relatório PDF). Vídeo local e processamento assíncrono requerem ambos.

---

## 7. Setup local passo a passo

### 7.1 Clonar o repositório

```bash
git clone https://github.com/rickdeu/startupscan-backend.git
cd startupscan-backend
```

### 7.2 Criar e activar ambiente virtual

```bash
# Criar ambiente virtual
python -m venv .venv

# Activar (Linux / macOS)
source .venv/bin/activate

# Activar (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activar (Windows cmd)
.venv\Scripts\activate.bat
```

O prompt deve mostrar `(.venv)` à esquerda quando o ambiente está activo.

### 7.3 Instalar dependências

```bash
pip install -r requirements.txt
```

> A instalação pode demorar alguns minutos — o projecto tem dependências pesadas como scikit-learn, moviepy, deepface e transformers.

### 7.4 Configurar variáveis de ambiente

Cria um ficheiro `.env` na raiz do projecto:

```bash
cp .env.example .env   # se existir exemplo
# ou cria manualmente
```

Conteúdo mínimo para desenvolvimento local:

```env
SECRET_KEY=django-insecure-muda-esta-chave-em-producao
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
```

Ver a secção [8. Variáveis de ambiente](#8-variáveis-de-ambiente) para a lista completa.

### 7.5 Aplicar migrações da base de dados

```bash
python manage.py migrate
```

Isto cria o ficheiro `db.sqlite3` com todas as tabelas.

### 7.6 Criar conta de administrador

```bash
python manage.py createsuperuser
```

Segue as instruções no terminal (username, email, password). Esta conta tem acesso total à plataforma e ao painel de admin em `/admin/`.

### 7.7 Recolher ficheiros estáticos

```bash
python manage.py collectstatic --noinput
```

### 7.8 (Opcional) Treinar o modelo de ML inicial

O sistema consegue avaliar pitches sem modelo pré-treinado (cria um em runtime), mas para melhores resultados treina explicitamente:

```bash
python manage.py train_model --model-output ai_models/pitch_model.pkl
```

Ver a secção [9. Treino do modelo de IA](#9-treino-do-modelo-de-ia) para opções avançadas.

### 7.9 Iniciar o servidor de desenvolvimento

```bash
python manage.py runserver 0.0.0.0:8000
```

Acede em: **http://localhost:8000**

### Resumo dos comandos

```bash
git clone https://github.com/rickdeu/startupscan-backend.git
cd startupscan-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# configura o .env
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py runserver 0.0.0.0:8000
```

---

## 8. Variáveis de ambiente

### Obrigatórias

| Variável | Descrição | Exemplo |
|---|---|---|
| `SECRET_KEY` | Chave secreta Django (OBRIGATÓRIA em produção) | `django-insecure-...` |
| `DJANGO_DEBUG` | Modo debug: `1` para dev, `0` para prod | `1` |

### Opcionais — Django

| Variável | Descrição | Default |
|---|---|---|
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por vírgula | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Origins CSRF confiáveis | — |
| `CORS_ALLOWED_ORIGINS` | Origins CORS permitidas | — |

### Opcionais — Base de dados

Por omissão o sistema usa SQLite. Para usar PostgreSQL em produção:

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | URL completa de conexão PostgreSQL | `postgres://user:pass@host:5432/db` |
| `POSTGRES_USER` | Utilizador PostgreSQL | `startupscan` |
| `POSTGRES_PASSWORD` | Password PostgreSQL | `password123` |
| `POSTGRES_DB` | Nome da base de dados | `startupscan` |
| `POSTGRES_HOST` | Host PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Porta PostgreSQL | `5432` |
| `DB_IGNORE_SSL` | Ignorar SSL na conexão BD: `1` / `0` | `0` |

### Opcionais — Cache e filas (Celery)

| Variável | Descrição | Default |
|---|---|---|
| `CELERY_BROKER_URL` | URL do broker Redis para Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Backend de resultados Celery | `redis://localhost:6379/0` |

### Opcionais — IA e APIs externas

| Variável | Descrição | Efeito sem a chave |
|---|---|---|
| `OPENAI_API_KEY` | Chave API OpenAI | Sistema usa modelo local |
| `OPENAI_MODEL` | Modelo GPT a usar | `gpt-4.1-mini` |
| `DID_API_KEY` | Chave API D-ID (vídeo realista) | Usa geração de vídeo local |
| `DID_API_BASE_URL` | Endpoint D-ID | `https://api.d-id.com` |
| `DID_VOICE_ID` | ID de voz D-ID | — |
| `EDGE_TTS_VOICE_PT_AO` | Voz TTS em português (Angola) | Voz default edge-tts |
| `WHISPER_MODEL` | Tamanho do modelo Whisper | `base` |

### Opcionais — Paths

| Variável | Descrição | Default |
|---|---|---|
| `AI_MODELS_DIR` | Directório para modelos treinados | `<BASE_DIR>/ai_models` |
| `DATA_DIR` | Directório para datasets | `<BASE_DIR>/data` |

> **Dica:** Em desenvolvimento, sem nenhuma API key, todas as funcionalidades de fallback local funcionam. Consegues avaliar pitches, gerar PDFs e vídeos locais sem qualquer custo externo.

---

## 9. Treino do modelo de IA

### Como funciona

O pipeline de ML usa scikit-learn com os seguintes passos:

1. **Carregamento de dados**: datasets CSV de pitches e dados financeiros
2. **Feature engineering**: TF-IDF sobre texto + features financeiras normalizadas
3. **Ensemble**: RandomForest + GradientBoosting + ExtraTrees (votação)
4. **Validação cruzada**: 5-fold KFold
5. **Augmentação**: 60x jitter para enriquecer dados escassos
6. **Serialização**: joblib (`.pkl`)

### Treinar com datasets default

```bash
python manage.py train_model --model-output ai_models/pitch_model.pkl
```

### Treinar com datasets personalizados

```bash
python manage.py train_model \
  --model-output ai_models/meu_modelo.pkl \
  --pitches-data data/meus_pitches.csv \
  --financials-data data/meus_financeiros.csv
```

### Retreinar via interface web

Vai a `/models/` (requer papel `analista` ou `admin`):

1. Faz upload dos datasets CSV
2. Clica em "Retreinar modelo"
3. O progresso aparece em tempo real
4. Ao concluir, o novo modelo pode ser activado

### Estrutura esperada dos datasets

**pitches.csv** (mínimo):
```csv
text,success_score
"A nossa plataforma conecta...",7.5
"Desenvolvemos uma solução...",6.2
```

**financials.csv** (mínimo):
```csv
revenue,growth_rate,profit_margin,burn_rate
150000,0.25,0.15,8000
```

---

## 10. Uso da plataforma

### Registo e login

1. Acede a `http://localhost:8000/register/`
2. Preenche nome, email, password e **escolhe o teu papel** (empreendedor, investidor, analista, público)
3. Após registo, serás redirecionado para o dashboard do teu papel
4. Para entrar novamente: `http://localhost:8000/login/`

### Como empreendedor

#### Submeter uma análise

1. Vai ao menu e clica em **"Analisar Pitch"** ou acede a `/analyze/form/`
2. Preenche:
   - Nome da startup e indústria
   - Texto do pitch (ou faz upload de documento/áudio/vídeo)
   - Dados financeiros (receita, crescimento, margem)
3. Clica em **"Analisar"** e aguarda (tipicamente 5–15 segundos)
4. Vais ser redirecionado para a página de resultados com o score e o relatório

#### Ver resultados

Na página de resultados (`/results/<id>/`) encontras:

- **Score de sucesso** (0–10) com gráfico visual
- **Nível de confiança** da previsão
- **8 categorias** avaliadas individualmente
- **Pontos fortes e fracos** identificados pelo modelo
- **Recomendações** práticas de melhoria

#### Descarregar artefactos

- **Relatório técnico PDF**: botão "Descarregar Relatório" → `/results/<id>/pdf/`
- **Pitch deck PDF**: botão "Gerar Pitch Deck" → `/results/<id>/pitch/pdf/`

#### Gerar vídeo explicativo

1. Na página de resultados, vai à secção de vídeo
2. Escolhe o modo: `auto`, `did_only`, ou `local_only`
3. (Opcional) Faz upload da foto do apresentador para detecção de género
4. Clica em **"Gerar Vídeo"** — o progresso actualiza-se em tempo real
5. Quando concluído, o vídeo está disponível para reprodução e download

#### Construtor de ideias

1. Acede a `/pitch/builder/`
2. Preenche todos os campos da ideia (problema, solução, mercado, etc.)
3. Clica em **"Gerar Pitch"** — o sistema cria o conteúdo narrativo
4. Exporta como PDF ou torna a ideia pública para feedback da comunidade

### Como investidor

1. Acede ao dashboard de investidor em `/investors/`
2. Navega pelas startups disponíveis com os seus scores
3. Clica em **"Expressar Interesse"** numa startup que te interessa
4. Escreve uma mensagem para o empreendedor
5. Acompanha o estado da conexão em `/connections/`

### Como analista

1. Usa o dashboard principal para ver todas as análises
2. Submete análises individuais ou em lote (upload CSV em `/batch/analyze/`)
3. Gere modelos de ML em `/models/`
4. Monitoriza o progresso de treino em tempo real

### Como público

1. Navega as ideias públicas em `/ideas/`
2. Abre uma ideia para ver os detalhes
3. Dá feedback com estrelas (1–5), endosso e comentário

---

## 11. Referência de endpoints

### Autenticação

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/login/` | Página de login |
| POST | `/login/` | Autenticar |
| GET | `/logout/` | Terminar sessão |
| GET | `/register/` | Página de registo |
| POST | `/register/` | Criar conta |
| POST | `/set-language/` | Mudar idioma da interface |

### Dashboard e navegação

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/` | Dashboard (redireciona por papel) |
| GET | `/home/` | Home baseada no papel |
| GET | `/investors/` | Dashboard investidor |

### Análise de pitch

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/analyze/form/` | Formulário de submissão |
| POST | `/analyze/form/` | Submeter pitch para análise |
| POST | `/analyze/` | API REST de análise |
| GET | `/results/<id>/` | Página de resultados |
| GET | `/results/<id>/pdf/` | Relatório técnico PDF |
| GET | `/results/<id>/pitch/pdf/` | Pitch deck PDF |

### Vídeo explicativo

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/results/<id>/video/generate/` | Iniciar geração de vídeo |
| POST | `/results/<id>/video/detect-gender/` | Detectar género do apresentador |
| GET | `/results/<id>/video/progress/<job_id>/` | Polling do progresso |

### Processamento em lote

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/batch/analyze/` | Submeter CSV para análise em lote |
| GET | `/batch/status/<batch_id>/` | Estado do lote |
| GET | `/batch/results/<batch_id>/` | Descarregar resultados |

### Gestão de modelos (analista / admin)

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/models/` | Painel de modelos |
| POST | `/model/retrain/` | Iniciar treino |
| GET | `/models/training/progress/<job_id>/` | Progresso do treino |
| GET | `/training/status/<task_id>/` | Estado da task Celery |

### Construtor de ideias

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/pitch/builder/` | Formulário de ideia |
| POST | `/pitch/builder/` | Submeter ideia |
| GET | `/pitch/builder/<id>/` | Ver / editar ideia |
| GET | `/pitch/builder/<id>/pdf/` | Exportar ideia como PDF |

### Ideias públicas

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/ideas/` | Lista de ideias públicas |
| GET | `/ideas/<id>/` | Detalhe de ideia pública |
| POST | `/ideas/<id>/feedback/` | Submeter feedback |

### Conexões

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/investors/interest/<analysis_id>/` | Expressar interesse |
| GET | `/connections/` | Hub de conexões |
| POST | `/connections/<interest_id>/update/` | Actualizar estado de conexão |

---

## 12. Execução com Docker Compose

O Docker Compose levanta o stack completo: aplicação web, PostgreSQL, Redis, worker Celery e scheduler Celery Beat.

### Pré-requisitos

- Docker Desktop instalado e em execução
- Ficheiro `.env` configurado (ver secção 8)

### Iniciar todos os serviços

```bash
docker-compose up -d
```

Serviços iniciados:

| Serviço | Porta | Descrição |
|---|---|---|
| `web` | 8000 | Aplicação Django (Gunicorn) |
| `db` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis (cache + broker Celery) |
| `celery-worker` | — | Worker para jobs assíncronos |
| `celery-beat` | — | Scheduler de tarefas periódicas |

Acede em: **http://localhost:8000**

### Comandos úteis

```bash
# Ver logs da aplicação em tempo real
docker-compose logs -f web

# Entrar no container da aplicação
docker-compose exec web bash

# Aplicar migrações
docker-compose exec web python manage.py migrate

# Criar superuser
docker-compose exec web python manage.py createsuperuser

# Treinar modelo inicial
docker-compose exec web python manage.py train_model \
  --model-output ai_models/pitch_model.pkl

# Parar todos os serviços
docker-compose down

# Parar e remover todos os volumes (apaga dados)
docker-compose down -v
```

### Volumes persistentes

| Volume | Conteúdo |
|---|---|
| `postgres_data` | Dados PostgreSQL |
| `redis_data` | Dados Redis |
| `media_volume` | Uploads de utilizadores |
| `static_volume` | Ficheiros estáticos recolhidos |
| `ai_models_volume` | Modelos ML treinados |

---

## 13. Deploy na Render (CI/CD)

O projecto tem deploy automático configurado para a [Render.com](https://render.com) via GitHub Actions.

### Configuração inicial

1. Cria um serviço Web na Render apontando para este repositório
2. A Render detecta automaticamente o `render.yaml` e configura o serviço
3. Copia o **Deploy Hook URL** das definições do serviço Render

### Configurar GitHub Secrets

No repositório GitHub, vai a **Settings → Secrets → Actions** e adiciona:

| Secret | Valor |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | URL do deploy hook da Render (obrigatório) |
| `RENDER_HEALTHCHECK_URL` | `https://<app>.onrender.com/login/` (opcional) |

### Configurar variáveis de ambiente na Render

No painel da Render, adiciona as variáveis de ambiente necessárias:

```
SECRET_KEY=<chave-forte-aleatória>
DJANGO_DEBUG=0
DATABASE_URL=<gerado-automaticamente-pela-render>
OPENAI_API_KEY=<opcional>
DID_API_KEY=<opcional>
```

### Fluxo de deploy

1. Faz push para a branch `main`
2. O GitHub Action (`.github/workflows/deploy-render-main.yml`) é activado
3. Executa testes e verificações
4. Chama o deploy hook da Render
5. A Render faz pull do código, instala dependências e reinicia o serviço

### Exposição externa gratuita (Cloudflare Tunnel)

Para expor o servidor local sem deploy:

```bash
# Instalar cloudflared
# https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/

# Criar túnel
cloudflared tunnel create startupscan

# Correr túnel
cloudflared tunnel run startupscan
```

Adiciona o subdomínio gerado a `DJANGO_ALLOWED_HOSTS` e `DJANGO_CSRF_TRUSTED_ORIGINS`.

---

## 14. Testes e validação

### Executar testes automáticos

```bash
python manage.py test
```

### Verificar configuração Django

```bash
python manage.py check
```

### Checklist de validação funcional

Após setup, valida os fluxos principais:

- [ ] Login e registo com cada papel
- [ ] Submissão de pitch com texto simples → score gerado
- [ ] Submissão de pitch com documento PDF
- [ ] Download de relatório técnico PDF
- [ ] Geração de pitch deck PDF (design automático)
- [ ] Geração de vídeo em modo `local_only`
- [ ] Treino de modelo pelo painel (analista/admin)
- [ ] Progresso em tempo real de treino e vídeo
- [ ] Construtor de ideias → geração → export PDF
- [ ] Fluxo de conexão investidor → empreendedor

---

## 15. Troubleshooting

### Erro: `SECRET_KEY environment variable must be set in production`

Estás a correr com `DJANGO_DEBUG=0` sem definir `SECRET_KEY`. Adiciona ao `.env`:

```env
SECRET_KEY=qualquer-chave-longa-e-aleatoria
DJANGO_DEBUG=1
```

### Vídeo D-ID falha

1. Verifica que `DID_API_KEY` está definida e tem créditos
2. A imagem do apresentador deve ser acessível via HTTPS (não local)
3. Testa com `local_only` para confirmar que o problema é só na API D-ID:
   ```
   modo: local_only
   ```

### PDF não gera

```bash
pip show reportlab   # deve mostrar versão instalada
```

Verifica também que o directório `MEDIA_ROOT` tem permissão de escrita:

```bash
ls -la media/        # deve ter permissões rw
```

### GPT não está a ser usado

Confirma que `OPENAI_API_KEY` está definida:

```bash
python manage.py shell
>>> import os; print(bool(os.getenv('OPENAI_API_KEY')))
True
```

### Migração falha

```bash
python manage.py migrate --run-syncdb
# ou
python manage.py migrate --fake-initial
```

### Overlay de submissão não desaparece

Limpa o cache do browser (`Ctrl + Shift + R`). O reset do overlay está implementado no `base.html`.

### Celery não processa jobs

Confirma que Redis está a correr:

```bash
redis-cli ping   # deve responder PONG
```

Inicia o worker manualmente:

```bash
celery -A startupscan worker --loglevel=info
```

### `ModuleNotFoundError` ao importar dependências

O ambiente virtual pode não estar activado:

```bash
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate.bat  # Windows
pip install -r requirements.txt
```

---

## 16. Documentação técnica adicional

O directório `docs/` contém scripts para gerar documentação técnica detalhada.

### Gerar PDF de engenharia de software

```bash
python docs/generate_engineering_pdf.py
```

Cria: `docs/Documentacao_Engenharia_Software.pdf`

### Gerar DOCX de engenharia de software

```bash
python docs/generate_engineering_docx.py
```

Cria: `docs/Documentacao_Engenharia_Software.docx`

---

## Contribuição

1. Faz fork do repositório
2. Cria uma branch descritiva: `git checkout -b feat/minha-funcionalidade`
3. Faz as alterações e testa
4. Faz push e abre um Pull Request para `main`

---

## Licença

Ver ficheiro `LICENSE` na raiz do repositório.
