# Motores de Avaliação DeepSeek + Ollama — Plano de Implementação

> Status: **implementado** na branch `feature/deepseek-ollama-ai-engines`
> Autor: Andre (com apoio de Claude Code)
> Data: 2026-09-09 (implementação em 2026-09-10)

## 1. Objetivo

Hoje o StartupScan avalia ideias/pitches com dois motores: **Local** (modelo ML treinado internamente) e **GPT** (OpenAI). Esta feature adiciona dois motores novos:

- **DeepSeek** — motor via API (estilo OpenAI-compatible), custeado, para planos pagos.
- **Ollama** — motor rodando localmente via um serviço Docker gerenciado pelo próprio backend, sem custo de API externa por chamada.

E redesenha a matriz de acesso por plano de assinatura, incluindo a criação de um plano **Free** que hoje não existe explicitamente no sistema.

## 2. Matriz de planos x motores (requisito de negócio)

| Plano | Local | GPT | DeepSeek | Ollama |
|---|---|---|---|---|
| **Trial** (novo usuário, primeiros dias) | ✅ | ✅ | ✅ | ✅ |
| **Free** (pós-trial, sem upgrade) | ✅ | ❌ | ❌ | ❌ |
| **Basic** | ❌ | ❌ | ✅ | ✅ |
| **Pro** | ✅ | ✅ | ✅ | ✅ |

Notas importantes:
- O plano **Trial** já existe no sistema hoje e funciona como um período de teste com acesso a um plano pago — mantém esse comportamento, agora cobrindo os 4 motores.
- O plano **Free** é uma peça nova: hoje, quando o trial expira sem conversão para pago, o usuário simplesmente fica bloqueado (ver seção 4.3). Precisamos criar esse plano e a transição para ele.
- **Basic não tem acesso a Local nem a GPT** — só aos dois motores novos. Isso é intencional pela regra de negócio definida, embora tecnicamente o fallback de erro (seção 6) ainda caia no Local nesse plano.

## 3. Estado atual do sistema (mapeamento de código)

### 3.1 Motor Local
- `startupscan_api/modeling.py` — `train_and_evaluate()` treina um `Pipeline` sklearn (TF-IDF + features numéricas via `ColumnTransformer`, testando RandomForest/ExtraTrees/GradientBoosting). `predict_success_score()` faz a inferência, com fallback para um "legacy model" (`prepare_features` em `startupscan_api/utils.py`).
- Orquestração de treino: `startupscan_api/services/model_training.py`.
- Registro do modelo ativo: `startupscan_api/services/model_registry.py` (`ai_models/model_registry.json`, `.pkl` em `ai_models/`).
- Runtime: `ensure_model_exists()` e `predict_pitch_score()`, chamados em `startupscan_api/views/pitch.py`.

### 3.2 Motor GPT
- `startupscan_api/modeling.py`, função `analyze_with_gpt(text, financial_data, metadata, language)`.
- Lê `OPENAI_API_KEY` / `OPENAI_MODEL` via `os.getenv` diretamente (não passa por `settings.py`).
- Usa a lib `openai` (`OpenAI(...).chat.completions.create(response_format={"type": "json_object"})`), com prompt system/user detalhado pedindo JSON estruturado (score, resumo, pontos fortes, `category_scores`, `investor_pitch`, etc.).
- Retorna a tupla `(score, report_dict, "gpt")`. Em erro ou key ausente, retorna `(None, {...}, "local-fallback")` — o caller então roda o motor Local como fallback.
- Também usado na geração de pitch (`services/pitch/generator.py`) e no vídeo explicativo (`services/pitch_video.py`).

### 3.3 Como o motor é escolhido hoje
- Campo `IdeaPitchSubmission.model_source` (`startupscan_api/models/idea.py`), `MODEL_SOURCE_CHOICES = [("local", "Local"), ("gpt", "GPT")]`, `max_length=10`.
- `PitchAnalysisSerializer.model_source` (`startupscan_api/serializers.py`), `ChoiceField`, default `"local"`.
- **Validação duplicada** em pelo menos 4 lugares: `views/pitch.py`, `views/api.py`, `views/idea.py`, `services/pitch/generator.py` — cada um faz `if model_source not in {"local", "gpt"}` na mão. Não existe um enum único compartilhado.
- Quando nada é informado, `views/pitch.py` escolhe `"gpt" if OPENAI_API_KEY else "local"`.
- Depois de rodar, `metadata["analysis_engine_requested"]` guarda o que foi pedido e `metadata["analysis_engine_used"]` guarda o que rodou de fato (podem divergir por causa do fallback). Consumido em relatórios PDF e filtros de dashboard/investidor.

### 3.4 Gating de GPT hoje
- `views/pitch.py` (`_check_pitch_gates`) chama `check_feature_access(user, 'gpt_analysis')`.
- `views/idea.py` bloqueia GPT para quem não é admin/analyst.
- **Achado importante**: `StartupPitchAnalyzer` (`views/api.py`) é um endpoint hoje **sem nenhum gating de plano** — qualquer chamada pode pedir `model_source=gpt`. Ver decisão 7.8.

### 3.5 Sistema de planos/assinatura (`subscriptions/`)
- `SubscriptionPlan.TIER_CHOICES = [trial, basic, pro]` — **não existe tier "free"** hoje. O "gratuito" é modelado como o próprio plano `trial` (padrão 7 dias), com acesso equivalente a um plano pago durante esse período.
- Feature flags booleanas no plano (`gpt_analysis`, `audio_upload`, `video_upload`, `pdf_report`, `pitch_gpt`, `video_generation`, etc.) e limites mensais (`analyses_per_month`, `videos_per_month`, ...). Métodos `has_feature()` / `is_within_limit()`.
- `Subscription.status` (`trialing/active/past_due/canceled/incomplete/inactive`), `trial_end`. `is_active` é uma **property calculada** (não persistida): para `status=trialing`, verifica `trial_end > now()` dinamicamente.
- Trial é criado automaticamente via sinal `post_save` em `User` (`subscriptions/signals.py`).
- Gating central: `subscriptions/mixins.py` — `_gate_check()`, exposto como `check_feature_access()` / `check_limit_access()`, mixin `SubscriptionGate`, decorator `subscription_required(...)`.
- Billing via Stripe (`subscriptions/stripe_sync.py`).

### 3.6 Gap confirmado: expiração de trial
Não existe hoje **nenhum job** (Celery beat, management command, sinal) que processe a expiração do trial. O `docker-compose.yml` sobe um serviço `celery-beat`, mas ele roda sem nenhuma tarefa periódica registrada em lugar nenhum do código. Quando o trial expira sem upgrade:
- `status` continua `"trialing"` no banco;
- `is_active` passa a `False` (calculado dinamicamente);
- `_gate_check` trata `not is_active` como bloqueio total — **o usuário fica sem acesso a nada, nem ao motor Local**.

Isso precisa ser corrigido como parte desta feature (ver seção 4.3).

### 3.7 Variáveis de ambiente / API keys
- `.env` contém `OPENAI_API_KEY`, `OPENAI_MODEL`, chaves Stripe, `DID_API_KEY`, `ELEVENLABS_API_KEY`.
- `backend/settings.py` carrega `.env` via `load_dotenv`, mas `OPENAI_API_KEY` **não** é exposto como `settings.OPENAI_API_KEY` — é lido direto via `os.getenv` dentro de `modeling.py`. Vamos seguir o mesmo padrão para as novas chaves, por consistência.

### 3.8 Docker
Existe `Dockerfile`, `celery/Dockerfile` e `docker-compose.yml` na raiz, mas estão **desatualizados/inconsistentes** com a estrutura atual do projeto:
- `docker-compose.yml` usa `build.context: ./backend` (não existe — o app Django vive na raiz do repo) e `gunicorn startupscan.wsgi:application` (o módulo real é `backend.wsgi:application`).
- `celery -A startupscan worker/beat` não bate com o nome real do app Celery.

**Decisão de escopo**: o conserto desse legado fica **fora do escopo** desta feature. Vamos adicionar o serviço `ollama` de forma isolada, sem depender do resto do compose estar correto.

## 4. Design da solução

### 4.1 Enum único de motores
Novo módulo `startupscan_api/engines.py`:

```python
from django.db import models

class AnalysisEngine(models.TextChoices):
    LOCAL = "local", "Local"
    GPT = "gpt", "GPT"
    DEEPSEEK = "deepseek", "DeepSeek"
    OLLAMA = "ollama", "Ollama"

def normalize_engine(value, default=AnalysisEngine.LOCAL) -> str:
    v = str(value or "").strip().lower()
    return v if v in AnalysisEngine.values else default
```

Esse módulo não deve importar nada pesado de `startupscan_api` nem de `subscriptions`, seguindo o padrão já usado por `startupscan_api/roles.py` (importado nos dois sentidos sem ciclo). Substitui as listas soltas duplicadas em `models/idea.py`, `serializers.py`, `views/pitch.py`, `views/api.py`, `views/idea.py`, `services/pitch/generator.py`, `views/dashboard.py`, `views/investor.py`.

`IdeaPitchSubmission.model_source` mantém `max_length=10` (cabe `"deepseek"`, 8 caracteres) — só precisa de uma migration para atualizar os `choices`.

### 4.2 Novos serviços de IA
Novo pacote `startupscan_api/services/ai_engines/` (evita inchar ainda mais `modeling.py`):

- **`prompts.py`** — extrai o prompt system/user hoje hardcoded dentro de `analyze_with_gpt` (incluindo os helpers já existentes `_build_uniqueness_key` e `_ensure_unique_report_language`, ambos em `modeling.py`, que evitam respostas genéricas/repetidas entre análises), para reuso entre GPT/DeepSeek/Ollama sem duplicar texto.
- **`deepseek_engine.py`** — `analyze_with_deepseek(text, financial_data, metadata, language="en") -> (score, report, engine_used)`, mesmo contrato de retorno de `analyze_with_gpt`, mesmo padrão de fallback. Usa o client `openai.OpenAI` apontando para um `base_url` customizado (DeepSeek expõe uma API compatível com a da OpenAI), evitando nova dependência.
  - Env vars: `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL` (default `deepseek-chat`), `DEEPSEEK_BASE_URL` (default `https://api.deepseek.com`).
- **`ollama_engine.py`** — `analyze_with_ollama(...)`, mesmo contrato, via `requests.post(f"{OLLAMA_BASE_URL}/api/chat", json={"model": OLLAMA_MODEL, "messages": [...], "format": "json", "stream": False}, timeout=OLLAMA_REQUEST_TIMEOUT)`.
  - Env vars: `OLLAMA_BASE_URL` (default `http://ollama:11434`, nome do serviço Docker), `OLLAMA_MODEL` (default `llama3.1:8b`), `OLLAMA_REQUEST_TIMEOUT` (default `120` segundos — CPU é lento).
  - O backend **não** tenta `ollama pull` sob demanda dentro do request do usuário (travaria minutos) — se o modelo não existir no host Ollama, cai direto no fallback Local.

### 4.3 Novo plano "Free" e transição trial → free
- `SubscriptionPlan.TIER_CHOICES` ganha `free`.
- Plano Free seedado com `local_analysis=True` e as demais flags de engine `False`; limites mensais equivalentes aos do trial atual.
- **Transição self-healing (sem infraestrutura nova de Celery beat)**: dentro de `subscriptions/mixins.py::_get_active_plan`, se `status == trialing`, `trial_end` já passou e não há `stripe_subscription_id` associado, a subscription é promovida para o plano Free (`status = active`). Essa checagem roda **antes** do bloqueio `not is_active` em `_gate_check` — senão o usuário pós-trial nunca sairia do bloqueio total.
- Essa transição é idempotente e dispara no primeiro acesso do usuário após a expiração, sem precisar de um cron/job novo.

### 4.4 Gating por plano
- `SubscriptionPlan` ganha os campos booleanos `local_analysis`, `deepseek_analysis`, `ollama_analysis` (mantendo `gpt_analysis` já existente).
- Trial ganha os 4 engines com flag `True` direto (espelha o plano pago sendo testado).
- Seed dos planos: **não existe `subscriptions/setup_subscription_plans.py`** — o arquivo real é o management command `subscriptions/management/commands/setup_subscription_plans.py`, com uma lista `PLANS` (um dict por combinação `tier`+`interval`) aplicada via `SubscriptionPlan.objects.update_or_create(lookup={tier, interval}, defaults=plan_data)`. O novo plano Free entra como mais uma entrada nessa lista (`tier=free`, `interval=once`, preço 0, sem `trial_days` relevante), e os planos existentes (Trial, Basic Monthly/Yearly, Pro Monthly/Yearly) ganham as 3 novas flags booleanas nos seus dicts.
- Nova função central em `subscriptions/mixins.py`:
  ```python
  _ENGINE_FEATURE_MAP = {
      AnalysisEngine.LOCAL: "local_analysis",
      AnalysisEngine.GPT: "gpt_analysis",
      AnalysisEngine.DEEPSEEK: "deepseek_analysis",
      AnalysisEngine.OLLAMA: "ollama_analysis",
  }

  def get_available_engines_for_user(user) -> list[str]: ...
  def check_engine_access(user, engine: str) -> tuple[bool, str]: ...
  ```
  Essa função central substitui as chamadas espalhadas de `check_feature_access(user, 'gpt_analysis')` por uma checagem genérica reutilizável em qualquer view.

### 4.5 Views, serializer e formulário
- `serializers.py` — `PitchAnalysisSerializer.model_source` passa a usar `AnalysisEngine.choices`.
- `views/pitch.py` — `_check_pitch_gates` chama `check_engine_access(user, model_source)`; execução vira um dicionário de dispatch (`{gpt: analyze_with_gpt, deepseek: analyze_with_deepseek, ollama: analyze_with_ollama}`, Local mantém branch próprio por causa da lógica de `ensure_model_exists`); a heurística fixa `"gpt" if OPENAI_API_KEY else "local"` vira `pick_default_engine_for_user(user)`, escolhendo o melhor motor disponível pro plano do usuário.
- `views/api.py` (`StartupPitchAnalyzer`) — hoje sem gating nenhum; **passa a ter gating de plano** ao expor os motores pagos/custeados (DeepSeek/Ollama consomem API paga ou CPU do servidor — expor sem controle seria um vazamento de custo).
- `views/idea.py` / `services/pitch/generator.py` — mesma normalização e mesmo gating para a geração de pitch completo.
- `views/dashboard.py`, `views/investor.py` — filtros de listagem trocam `{"all", "local", "gpt"}` por `{"all"} | AnalysisEngine.values`.
- Templates (`templates/analyzer/pitch_form.html`, `idea_pitch_form.html`, `superadmin/templates/superadmin/pitch_form.html`) — os rádios de motor hoje são hardcoded (2 opções); passam a iterar sobre `available_engines`, injetado no contexto da view via `get_available_engines_for_user(request.user)`. Novas chaves i18n (`pitch_form_engine_deepseek*`, `pitch_form_engine_ollama*`) em `startupscan_api/i18n.py`, replicando o padrão das chaves `_gpt*` já existentes nos 7 idiomas suportados.

### 4.6 Docker — serviço Ollama
Adição isolada ao `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - startupscan_network

  ollama-init:
    image: ollama/ollama:latest
    depends_on: [ollama]
    entrypoint: ["/bin/sh", "-c"]
    command: >
      "sleep 3 && OLLAMA_HOST=http://ollama:11434 ollama pull ${OLLAMA_MODEL:-llama3.1:8b}"
    networks: [startupscan_network]
    restart: "no"

volumes:
  ollama_data:
```

O serviço `ollama-init` roda uma vez, baixa o modelo default e encerra — padrão recomendado pelo próprio Ollama para warm-up, evitando lógica de pull dentro do código Django.

## 5. Variáveis de ambiente novas

| Variável | Default sugerido | Descrição |
|---|---|---|
| `DEEPSEEK_API_KEY` | — (obrigatória) | Chave de API da DeepSeek |
| `DEEPSEEK_MODEL` | `deepseek-chat` | Modelo usado nas chamadas |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | Endpoint compatível com OpenAI SDK |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Host do serviço Ollama (nome do serviço Docker) |
| `OLLAMA_MODEL` | `llama3.1:8b` | Modelo local usado nas chamadas |
| `OLLAMA_REQUEST_TIMEOUT` | `120` | Timeout em segundos (CPU é lento) |

## 6. Fallback e resiliência

Réplica do padrão já usado pelo GPT: se DeepSeek ou Ollama falharem (erro de rede, timeout, JSON inválido, key ausente), a função retorna `(None, {...}, "local-fallback")` e o caller roda o motor Local. Isso mantém `analysis_engine_requested` (o que o usuário pediu) e `analysis_engine_used` (o que realmente rodou) consistentes para os relatórios.

**Nota de produto**: como o plano Basic não tem `local_analysis=True`, esse fallback técnico "vaza" acesso ao motor Local em caso de erro de infraestrutura — decisão consciente para não deixar o usuário sem resposta nenhuma quando a API externa cai.

## 7. Riscos e cuidados

- `model_source` (`max_length=10`) comporta `"deepseek"` sem alterar o tamanho do campo.
- A transição preguiçosa trial→free precisa rodar **antes** da checagem `is_active` em `_gate_check`, senão o usuário pós-trial nunca sai do bloqueio total.
- Timeout do Ollama em CPU pode ser alto (60-120s) — dentro do escopo síncrono atual (paridade com GPT), mas pode exigir, no futuro, rodar via Celery task assíncrona em vez de síncrono no request HTTP.
- `docker-compose.yml`/`Dockerfile` legados continuam desatualizados — fora do escopo desta feature, mas deve ser tratado separadamente antes de um deploy real via Docker.

## 8. Checklist de verificação

- [ ] `python manage.py makemigrations --check` limpo após as mudanças em `subscriptions/models.py` e `startupscan_api/models/idea.py`.
- [ ] Usuários de teste em cada plano (free/basic/pro) confirmam que `get_available_engines_for_user` retorna a matriz correta da seção 2.
- [ ] `docker-compose up ollama ollama-init` sobe isoladamente; `curl http://localhost:11434/api/tags` lista o modelo baixado.
- [ ] Submissão de pitch testada com cada motor (mock de DeepSeek/GPT em teste automatizado; Ollama local real em teste manual), incluindo o caminho de fallback quando a API externa falha.
- [ ] `analysis_engine_requested` vs `analysis_engine_used` continuam divergindo corretamente nos relatórios PDF/dashboard quando há fallback.

## 9. Arquivos a criar/editar (resumo)

**Novos:**
- `startupscan_api/engines.py`
- `startupscan_api/services/ai_engines/prompts.py`
- `startupscan_api/services/ai_engines/deepseek_engine.py`
- `startupscan_api/services/ai_engines/ollama_engine.py`
- Migration nova em `subscriptions/migrations/` e `startupscan_api/migrations/`

**Editados:**
- `subscriptions/models.py`, `subscriptions/mixins.py`, `subscriptions/management/commands/setup_subscription_plans.py`
- `startupscan_api/models/idea.py`, `startupscan_api/serializers.py`
- `startupscan_api/views/pitch.py`, `views/api.py`, `views/idea.py`, `views/dashboard.py`, `views/investor.py`
- `startupscan_api/services/pitch/generator.py`
- `startupscan_api/i18n.py`
- `startupscan_api/templates/analyzer/pitch_form.html`, `idea_pitch_form.html`
- `startupscan_api/templatetags/dict_extras.py` (filtros `engine_label`/`engine_desc`/`idea_engine_label`)
- `docker-compose.yml`, `.env` local (sem `.env.example` versionado no repo)

## 10. Notas de implementação (desvios do plano original)

- **Nomenclatura visível ao usuário desacoplada do fornecedor.** Os identificadores internos continuam `local`/`gpt`/`deepseek`/`ollama` (DB, código, dispatch), mas os rótulos exibidos no formulário não citam o fornecedor: Local → "motor rápido", Ollama → "motor equilibrado", DeepSeek → "motor avançado", GPT → "motor elite". Decisão do usuário, aplicada nos 7 idiomas (`startupscan_api/i18n.py`), com inglês como referência.
- **`superadmin/templates/superadmin/pitch_form.html` não precisou de alteração** — `PitchAnalysis` não tem campo `model_source` (fica em `metadata` JSON), só `IdeaPitchSubmission` tem esse campo, e o form do superadmin para ideias (`idea_form.html`) já resolve o `<select>` automaticamente via `AnalysisEngine.choices` no `ModelForm`.
- **Geração de pitch completo (`IdeaPitchSubmission`) reaproveita as mesmas flags de análise** (`local_analysis`/`gpt_analysis`/`deepseek_analysis`/`ollama_analysis`) em vez de introduzir `pitch_deepseek`/`pitch_ollama` paralelos a `pitch_gpt`. O campo `pitch_gpt` existente foi mantido no modelo (usado em outros lugares: superadmin CRUD, `templates/subscriptions/plans.html`), mas deixou de ser a checagem usada em `views/idea.py` para a ação "gerar pitch" — substituído por `check_engine_access(user, submission.model_source)`, genérico para os 4 motores.
- **`StartupPitchAnalyzer` (`views/api.py`) só ganhou gating para GPT/DeepSeek/Ollama.** O motor `local` continua sem gate nesse endpoint específico, preservando o comportamento histórico de acesso anónimo (o endpoint não exige autenticação); isso evita quebrar integrações externas que dependiam de análise local sem login, enquanto ainda impede o vazamento de custo dos motores pagos/pesados.
- **`docker-compose.yml` já não estava desatualizado** — um merge de `main` anterior a esta implementação já tinha corrigido `context`/`wsgi`/`celery -A`. Só foi necessário adicionar os serviços `ollama` e `ollama-init` (+ volume `ollama_data`), sem tocar no resto.
- **Não existe `.env.example` versionado no repo**; as novas variáveis (`DEEPSEEK_*`, `OLLAMA_*`) foram documentadas aqui e adicionadas ao `.env` local (gitignored) para desenvolvimento.
- **Prompt de análise consolidado**: `analyze_with_gpt` (`modeling.py`) foi refatorado para usar `startupscan_api/services/ai_engines/prompts.py::build_pitch_analysis_prompts`, eliminando a duplicação de ~80 linhas de prompt que existiria entre GPT/DeepSeek/Ollama.
- **Validado localmente** (branch `feature/deepseek-ollama-ai-engines`): `manage.py check`, suíte de testes completa (35 testes, todos passando), `setup_subscription_plans` criando os 6 planos (incluindo Free), e testes manuais via `manage.py shell` confirmando a matriz de acesso por plano (Free=local, Basic=deepseek+ollama, Pro=todos, Trial=todos) e a transição preguiçosa trial→Free.
