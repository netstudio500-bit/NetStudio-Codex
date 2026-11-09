# NetStudio-Codex Architecture

## 📐 Visão Geral

NetStudio-Codex é construído com uma arquitetura modular que separa responsabilidades de forma clara:

```
┌─────────────────────────────────────────────────┐
│              UI / Frontend Layer                │
│         (React Dashboard + API Client)          │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           API Layer (FastAPI)                   │
│    (REST Endpoints + WebSocket Support)        │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│        Core Orchestration Layer                 │
│  (Runtime, Scheduler, State Management)        │
└──────────┬──────────────────────┬───────────────┘
           │                      │
    ┌──────▼──────┐        ┌──────▼──────┐
    │              │        │              │
┌───▼────────┐ ┌──▼────────▼──┐ ┌──────┬──▼──┐
│   Agent    │ │  Memory      │ │Tools │    │
│   Core     │ │  System      │ │Reg.  │    │
├────────────┤ ├──────────────┤ ├──────┼────┤
│ • LLM      │ │ • Vector     │ │Builtin    │
│ • Config   │ │ • Episodic   │ │Tools      │
│ • Event    │ │ • Persistent │ │          │
└────────────┘ └──────────────┘ └──────────┘
                                     │
                ┌────────────────────▼──────────┐
                │   Plugin System               │
                │   (Hot-Reload Support)       │
                └───────────────────────────────┘
```

## 🔧 Componentes Principais

### 1. Core Module

**Responsabilidade:** Definições base e configurações centralizadas.

**Arquivos principais:**
- `core/agent.py` - Definição de agente base
- `core/llm/` - Integração com Ollama
- `core/config.py` - Gerenciamento de configuração
- `core/events.py` - Sistema de eventos
- `core/logger.py` - Logging centralizado

**Interfaces:**
```python
class Agent:
    name: str
    description: str
    system_prompt: str
    
    async def execute(self, task: Task) -> Result
    async def think(self, context: Context) -> Plan
    async def remember(self, memory: Memory) -> None

class LLMProvider:
    async def generate(self, prompt: str) -> str
    async def embed(self, text: str) -> List[float]
```

### 2. Runtime Module

**Responsabilidade:** Execução de tarefas e gerenciamento de estado.

**Arquivos principais:**
- `runtime/executor.py` - Executor de tarefas
- `runtime/state.py` - State machine
- `runtime/scheduler.py` - Agendador
- `runtime/context.py` - Contexto de execução

**Flow:**
```
Task Input
    ↓
Validação
    ↓
Execution Context
    ↓
Task Execution Loop
    ├── Fetch State
    ├── Execute Step
    ├── Update State
    └── Check Completion
    ↓
Result + Checkpoints
```

### 3. Memory Module

**Responsabilidade:** Persistência e recuperação de informações.

**Tipos de Memória:**
- **Vector Memory:** Embeddings para similarity search
- **Episodic Memory:** Histórico de execuções
- **Persistent Storage:** SQLite/PostgreSQL

**Arquivos principais:**
- `memory/vector_store.py` - Vector embeddings
- `memory/episodic.py` - Memória episódica
- `memory/persistence.py` - Persistência
- `memory/models.py` - Data models

### 4. Tools Module

**Responsabilidade:** Registry e execução de ferramentas.

**Tipos de Ferramentas Built-in:**
- File Operations (read, write, execute)
- Web Access (HTTP requests)
- Shell Commands (execution with sandbox)
- Search (vector search)
- Database (queries)

**Arquivos principais:**
- `tools/registry.py` - Registry central
- `tools/builtin/` - Ferramentas padrão
- `tools/loader.py` - Carregador dinâmico
- `tools/sandbox.py` - Sandbox de execução

### 5. Planner Module

**Responsabilidade:** Decompor objetivos em planos executáveis.

**Estratégias:**
- ReAct (Reasoning + Acting)
- Chain-of-Thought
- Hierarchical Planning
- Dynamic Replanning

**Arquivos principais:**
- `planner/strategies/` - Implementações de estratégias
- `planner/reasoning.py` - Motor de raciocínio
- `planner/validator.py` - Validação de planos

### 6. Recovery Module

**Responsabilidade:** Recuperação de falhas e rollback.

**Mecanismos:**
- Checkpoints automáticos
- State snapshots
- Rollback de operações
- Diagnostics automáticos

**Arquivos principais:**
- `recovery/checkpoints.py` - Gerenciamento de checkpoints
- `recovery/snapshots.py` - Snapshots de estado
- `recovery/diagnostics.py` - Diagnóstico de erros

### 7. Workspace Module

**Responsabilidade:** Isolamento de contexto e projetos.

**Features:**
- Multi-workspace support
- File abstraction layer
- Context isolation
- Workspace persistence

**Arquivos principais:**
- `workspace/manager.py` - Gerenciador de workspace
- `workspace/project.py` - Definição de projeto
- `workspace/files.py` - Abstraçãode files

### 8. Plugin System

**Responsabilidade:** Extensibilidade e custom functionality.

**Features:**
- Dynamic plugin loading
- Plugin interfaces
- Hot-reload support
- Dependency injection

**Arquivos principais:**
- `plugins/loader.py` - Plugin loader
- `plugins/base.py` - Base classes
- `plugins/registry.py` - Plugin registry

### 9. UI Layer

**Responsabilidade:** Interface web e API.

**Backend:**
- FastAPI
- WebSocket support
- RESTful API
- Authentication

**Frontend:**
- React/Vue
- Real-time updates
- Dashboard
- Console

**Arquivos principais:**
- `ui/backend/app.py` - FastAPI app
- `ui/frontend/` - React components

## 🔄 Data Flow

### Execution Flow

```
1. User Input
   ↓
2. API Endpoint (POST /tasks)
   ↓
3. Task Creation + Validation
   ↓
4. Agent Selection
   ↓
5. Planner: Generate Plan
   ↓
6. Runtime: Execute Loop
   ├─ Fetch Memory Context
   ├─ Call LLM for Decision
   ├─ Execute Tool/Action
   ├─ Update Memory
   ├─ Create Checkpoint
   └─ Continue or Complete?
   ↓
7. Result Aggregation
   ↓
8. Return Result + Metadata
```

### Memory Access Pattern

```
Agent needs context
   ↓
Memory Query (vector search)
   ↓
Retrieve from Vector Store
   ↓
Enrich with Episodic Context
   ↓
Return to Agent
   ↓
Agent augments prompt
   ↓
LLM Call
```

## 🏗️ Dependency Management

### Sem Dependências Circulares

```
Core
  ↑
  │ (depend on)
  │
Runtime ← Memory ← Vector Store (Chroma)
  ↑         ↑
  │         └─ Persistence (SQLAlchemy)
  │
Planner
  ↑
  │
Tools
  ↑
  │
Workspace
  ↑
  │
Plugins
  ↑
  │
UI (FastAPI)
```

## 🔌 Plugin Architecture

### Plugin Interface

```python
class BasePlugin:
    name: str
    version: str
    
    async def initialize(self, context: PluginContext) -> None
    async def execute(self, input_data: Any) -> Any
    async def cleanup(self) -> None
```

### Plugin Types

1. **Tool Plugins** - Adicionar ferramentas customizadas
2. **Strategy Plugins** - Novas estratégias de planejamento
3. **Memory Plugins** - Novos tipos de memória
4. **LLM Plugins** - Novos provedores de LLM
5. **UI Plugins** - Componentes customizados

## 📦 Configuration

### Configuração Hierárquica

```
1. .env (environment variables)
2. config.yaml (user configuration)
3. Programmatic override (runtime)
```

### ConfigManager

```python
config = ConfigManager()
config.get("ollama.model", default="llama2")
config.set("agent.timeout", 300)
config.reload()
```

## 🧪 Testing Strategy

### Níveis de Teste

1. **Unit Tests** - Testes isolados de componentes
2. **Integration Tests** - Testes entre módulos
3. **E2E Tests** - Testes completos de fluxo
4. **Performance Tests** - Benchmarks

### Test Fixtures

- Mock LLM responses
- Test databases
- Temporary workspaces
- Sample memory data

## 🚀 Deployment

### Local Development

```bash
python -m netstudio.main --dev
```

### Production

```bash
docker-compose up -d
```

### Configuration by Environment

- `development` - Debug enabled, mock services
- `testing` - Isolated, fast, ephemeral
- `production` - Optimized, hardened, monitored

## 🔐 Security Considerations

1. **Tool Sandbox** - Isolamento de execução
2. **Memory Encryption** - Dados sensíveis criptografados
3. **API Authentication** - Token-based auth
4. **Input Validation** - Sanitização de inputs
5. **Rate Limiting** - Proteção contra abuse

## 📊 Monitoring & Observability

### Métricas

- Task execution time
- Memory usage
- LLM API calls
- Tool execution stats
- Error rates

### Logging

- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Centralized log aggregation

### Tracing

- OpenTelemetry integration
- Distributed tracing
- Span context propagation
