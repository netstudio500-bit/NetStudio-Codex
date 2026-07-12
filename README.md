# NetStudio-Codex

**Um Codex Local, Gratuito e Modular para Agentes de IA**

NetStudio-Codex é uma plataforma modular de código aberto que permite construir e gerenciar agentes de IA localmente, utilizando Ollama como provedor padrão de LLM. Sem dependências de serviços cloud pagos.

## 🎯 Objetivos

- ✅ Executar 100% localmente
- ✅ Suporte nativo a Ollama
- ✅ Arquitetura modular e extensível
- ✅ Zero dependência de OpenAI para funcionalidade básica
- ✅ Fácil integração de ferramentas e agentes
- ✅ Sistema de memória persistente
- ✅ Recuperação automática de falhas
- ✅ Interface web amigável

## 🏗️ Arquitetura

```
NetStudio-Codex/
├── core/                    # Núcleo do sistema
│   ├── agent/              # Definições e gerenciamento de agentes
│   ├── llm/                # Provedor de LLM (Ollama)
│   └── config/             # Configuração centralizada
├── runtime/                # Engine de execução
│   ├── executor/           # Executor de tarefas
│   ├── state/              # Gerenciamento de estado
│   └── scheduler/          # Agendador de tarefas
├── planner/                # Motor de planejamento
│   ├── strategies/         # Estratégias de planejamento
│   └── reasoning/          # Raciocínio e lógica
├── memory/                 # Sistema de memória
│   ├── vector/             # Memória vetorial
│   ├── episodic/           # Memória episódica
│   └── persistence/        # Persistência de dados
├── tools/                  # Registry de ferramentas
│   ├── builtin/            # Ferramentas built-in
│   ├── registry/           # Registro de ferramentas
│   └── loader/             # Carregador dinâmico
├── workspace/              # Gerenciamento de workspace
│   ├── project/            # Projetos
│   └── files/              # Gerenciamento de arquivos
├── recovery/               # Sistema de recuperação
│   ├── checkpoints/        # Pontos de verificação
│   └── rollback/           # Rollback de estado
├── plugins/                # Sistema de plugins
│   ├── loader/             # Carregador de plugins
│   └── interfaces/         # Interfaces de plugins
├── ui/                     # Interface Web
│   ├── frontend/           # React/Vue frontend
│   ├── backend/            # Backend FastAPI/Express
│   └── websocket/          # Comunicação real-time
├── tests/                  # Testes
│   ├── unit/               # Testes unitários
│   ├── integration/        # Testes de integração
│   └── e2e/                # Testes end-to-end
├── docs/                   # Documentação
├── examples/               # Exemplos de uso
└── scripts/                # Scripts de utilidade
```

## 🚀 Quick Start

### Requisitos
- Python 3.11+
- Ollama instalado e rodando localmente
- Poetry ou pip para gerenciamento de dependências

### Instalação

```bash
# Clone o repositório
git clone https://github.com/netstudio500-bit/NetStudio-Codex.git
cd NetStudio-Codex

# Instale as dependências
pip install -e .

# Configure o ambiente
cp .env.example .env

# Inicie a aplicação
python -m netstudio.main
```

## 📦 Módulos Principais

### Core
Núcleo do sistema com definições de agentes e provedores de LLM.

### Runtime
Engine de execução que gerencia o ciclo de vida das tarefas.

### Planner
Motor de planejamento que quebra objetivos em passos executáveis.

### Memory
Sistema de memória persistente com suporte a embeddings vetoriais.

### Tools
Registry dinâmico de ferramentas que agentes podem usar.

### Workspace
Gerenciador de projetos e contextos de trabalho.

### Recovery
Sistema automático de recuperação de falhas com checkpoints.

### Plugins
Sistema extensível para adicionar funcionalidades customizadas.

### UI
Interface web para interação com o sistema.

## 🛠️ Desenvolvimento

```bash
# Instale dependências de desenvolvimento
pip install -e ".[dev]"

# Execute os testes
pytest tests/

# Execute com modo debug
python -m netstudio.main --debug
```

## 📖 Documentação

- [ROADMAP.md](./ROADMAP.md) - Plano de desenvolvimento
- [ARCHITECTURE.md](./docs/ARCHITECTURE.md) - Detalhes arquiteturais
- [API.md](./docs/API.md) - Documentação de API
- [PLUGINS.md](./docs/PLUGINS.md) - Guia de desenvolvimento de plugins

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

MIT License - veja o arquivo LICENSE para mais detalhes.

## 📞 Suporte

- Issues: [GitHub Issues](https://github.com/netstudio500-bit/NetStudio-Codex/issues)
- Discussões: [GitHub Discussions](https://github.com/netstudio500-bit/NetStudio-Codex/discussions)
- Email: contato@netstudio.dev
