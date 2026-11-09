# Pull Request Template

## Resumo
Descreva em poucas linhas o que este PR altera e por quê.

---

## Alterações principais
- Adiciona gerador de piadas (módulo sync/async) com exemplo e testes.
- Adiciona app To‑Do com armazenamento local em disco, CLI e UI que usa localStorage.
- Inclui testes unitários para ambos os recursos.

### Arquivos adicionados
- `netstudio/joke.py`
- `examples/joke_cli.py`
- `tests/test_joke.py`
- `netstudio/todo.py`
- `examples/todo_cli.py`
- `examples/todo_localstorage.html`
- `tests/test_todo.py`

---

## Como testar localmente
1. Instale dependências: `poetry install`
2. Teste o gerador de piadas:
   - `python examples/joke_cli.py`
3. Teste o To‑Do (CLI):
   - `python examples/todo_cli.py add "Comprar leite"`
   - `python examples/todo_cli.py list`
4. Abra a UI localStorage:
   - Abra `examples/todo_localstorage.html` no navegador
5. Rode a suíte de testes:
   - `pytest`

---

## Observações / Checklist
- [ ] Os testes passam localmente
- [ ] Lint e formatação aplicados (black/isort/ruff)
- [ ] Verificar tratamento de erros/timeouts (joke)
- [ ] Confirmar local padrão da store: `~/.netstudio_todos.json`
- [ ] Considerar adicionar retries/caching/logging
- [ ] (opcional) Adicionar endpoint HTTP (FastAPI) antes do merge

---

## Labels sugeridos
`feat`, `tests`, `chore`

## Reviewers sugeridos
(Adicionar reviewers da equipe aqui)
