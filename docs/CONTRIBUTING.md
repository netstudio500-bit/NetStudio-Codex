# Contributing to NetStudio-Codex

## 🤝 Código de Conduta

Este projeto adota um Código de Conduta aberto e inclusivo. Esperamos que todos os participantes o respeitem.

## 🚀 Começando

### Requisitos
- Python 3.11+
- Poetry ou pip
- Git
- Ollama instalado e rodando

### Setup de Desenvolvimento

```bash
# Clone o repositório
git clone https://github.com/netstudio500-bit/NetStudio-Codex.git
cd NetStudio-Codex

# Crie um virtual environment
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale as dependências
pip install -e ".[dev]"

# Instale pre-commit hooks
pre-commit install

# Execute os testes
pytest
```

## 📝 Processo de Contribuição

### 1. Crie uma Issue

Antes de começar a trabalhar, crie uma issue descrevendo:
- O problema ou feature
- Comportamento esperado
- Contexto relevante

### 2. Fork & Branch

```bash
# Fork o repositório no GitHub
# Clone seu fork
git clone https://github.com/YOUR_USERNAME/NetStudio-Codex.git
cd NetStudio-Codex

# Crie uma branch
git checkout -b feature/nome-da-feature
# ou
git checkout -b fix/nome-do-bug
```

### 3. Desenvolva

```bash
# Faça suas mudanças
# Certifique-se de escrever testes
# Execute os testes
pytest

# Verifique a qualidade do código
black .
isort .
flake8 netstudio/
mypy netstudio/
```

### 4. Commit

```bash
# Use mensagens descritivas
git commit -m "feat: adicionar nova estratégia de planejamento"
git commit -m "fix: corrigir bug no sistema de memória"
git commit -m "docs: atualizar documentação de API"

# Formato: <tipo>: <descrição>
# Tipos: feat, fix, docs, style, refactor, perf, test, chore
```

### 5. Push & Pull Request

```bash
# Push para seu fork
git push origin feature/nome-da-feature

# Crie um Pull Request no GitHub
# Inclua:
# - Descrição clara do que foi mudado
# - Link para a issue relacionada
# - Screenshots (se aplicável)
# - Checklist de testes
```

## 📋 Checklist de Pull Request

- [ ] Código segue o estilo do projeto (black, isort)
- [ ] Testes adicionados e passando
- [ ] Documentação atualizada
- [ ] Commit messages descritivas
- [ ] Sem mudanças não relacionadas
- [ ] Sem secrets ou dados sensíveis
- [ ] Sem breaking changes (ou bem documentado)

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── unit/              # Testes unitários
├── integration/       # Testes de integração
├── e2e/              # Testes end-to-end
├── fixtures/         # Data fixtures
└── conftest.py       # Configuração pytest
```

### Escrevendo Testes

```python
import pytest
from netstudio.core.agent import Agent

class TestAgent:
    @pytest.fixture
    def agent(self):
        return Agent(name="test-agent")
    
    def test_agent_initialization(self, agent):
        assert agent.name == "test-agent"
    
    @pytest.mark.asyncio
    async def test_agent_execution(self, agent):
        result = await agent.execute(task)
        assert result.success
```

### Rodando Testes

```bash
# Todos os testes
pytest

# Testes específicos
pytest tests/unit/
pytest tests/unit/test_agent.py
pytest -k "test_agent_execution"

# Com cobertura
pytest --cov=netstudio --cov-report=html
```

## 📚 Documentação

### Docstrings

```python
def execute_task(task: Task) -> Result:
    """
    Execute uma tarefa usando o agente.
    
    Args:
        task: A tarefa a executar
        
    Returns:
        Resultado da execução
        
    Raises:
        TaskError: Se a execução falhar
        
    Example:
        >>> agent = Agent()
        >>> result = agent.execute(task)
    """
    pass
```

### Type Hints

Sempre use type hints:

```python
from typing import List, Optional

def search_memory(
    query: str,
    limit: int = 10,
    threshold: Optional[float] = None
) -> List[MemoryItem]:
    pass
```

## 🎨 Style Guide

### Python

- Use Black para formatting (100 caracteres)
- Use isort para imports
- Use mypy para type checking
- Use flake8 para linting

```bash
# Auto-format
black netstudio/
isort netstudio/
```

### Commits

```
<type>(<scope>): <subject>

<body>

<footer>

Exemplo:
feat(memory): adicionar vector search

Implementa busca de similaridade usando embeddings.
Utiliza Chroma como vector store.

Fixes #123
```

### Branches

- `feature/...` - Novas features
- `fix/...` - Bug fixes
- `docs/...` - Documentação
- `refactor/...` - Refatoração
- `perf/...` - Performance

## 🔄 Review Process

1. **Automated Checks** - CI/CD pipeline
2. **Code Review** - Revisão de pares
3. **Approval** - Aprovação de maintainers
4. **Merge** - Merge para main

## 📞 Comunicação

- **Issues** - Bugs e features
- **Discussions** - Perguntas e ideias
- **Email** - contato@netstudio.dev

## 🙏 Obrigado

Sua contribuição faz diferença!
