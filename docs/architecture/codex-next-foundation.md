# CODEX NEXT: fundação arquitetural

## Missão

O CODEX NEXT é concebido como um agente local de engenharia de software para Windows, orientado a analisar, planejar, modificar, validar e evoluir projetos de forma segura, auditável e controlada.

## Princípios fundadores

1. Arquitetura antes do código.
2. Evidência antes da conclusão.
3. Segurança antes da velocidade.
4. Simplicidade antes da complexidade.
5. Uma responsabilidade por módulo.
6. Uma fonte da verdade por domínio.
7. Nenhuma alteração destrutiva sem autorização.

## Fluxo canônico

`UI -> IPC -> Runtime -> Planner -> Agent Core -> Permission Center -> Tool Registry -> Model Provider`

Integrações diretas que atravessem essas fronteiras devem ser tratadas como dívida arquitetural e justificadas explicitamente.

## Módulos canônicos

Runtime, Planner, Agent Core, Tool Registry, Permission Center, Checkpoint Manager, Recovery, Timeline, Health Center, Doctor, Update Sentinel, Model Manager, Model Provider e Workspace.

## Agent Core

O Agent Core recebe planos, coordena execução, solicita permissões, aciona ferramentas, controla contexto, valida resultados, registra eventos e replaneja quando necessário. Não deve manipular UI, acessar filesystem diretamente, executar shell diretamente ou chamar o provedor local sem a abstração de Model Provider.

Estados mínimos: `IDLE`, `PLANNING`, `WAITING_PERMISSION`, `RUNNING_TOOL`, `VALIDATING`, `REPLANNING`, `COMPLETED`, `FAILED` e `CANCELLED`.

## Regra de implementação

Documentos conceituais não comprovam que um componente exista. Cada capacidade deve ser confirmada no código e por validação executável antes de ser marcada como implementada.
