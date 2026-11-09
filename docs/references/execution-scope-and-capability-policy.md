# Escopo de execução e política de capacidades

Referência arquitetural extraída da auditoria de APIs administrativas e de execução. Não replica API externa.

Uma execução deve possuir escopo resolvido antes do loop de tools:

`ExecutionContext -> ScopeRef -> PolicySnapshot -> ToolRegistry view`

O modelo não escolhe workspace, promove role ou reinterpreta escopo pelo prompt. O host resolve contexto e apresenta somente capacidades permitidas.

## Actor e principal

Usuários e service accounts possuem regras diferentes. Preservar `ActorRef`/`PrincipalRef` capaz de representar humano, serviço ou agente gerenciado. Nome e email são atributos de exibição, não identidade operacional.

## Membership e concessão

Membership implícita e explícita têm semânticas diferentes. Uma remoção pode reverter ao estado implícito. Não persistir apenas `role = X`; preservar origem da concessão como `implicit`, `explicit` ou `inherited`.

Solicitação de acesso não é autorização ativa. Fluxos futuros de delegação devem preservar estados como `pending`, `approved`, `expired` e `revoked`, sem expor capability ao runtime antes da política efetiva ser resolvida.

## ToolRegistry

Roles administrativas não entram no prompt. O host converte identidade, escopo e memberships em política efetiva. O `ToolRegistry` produz uma visão filtrada. Tools podem declarar leitura, escrita, execução local, rede ou administração. Classificação ausente permanece `unclassified`; nunca vira silenciosamente `read_only`.

## Ciclo de vida e idempotência

Arquivado é diferente de excluído. Recursos arquivados podem continuar em auditoria sem serem selecionáveis para novas execuções.

Revoke, detach e cleanup devem preferir semântica idempotente quando seguro. Isso não elimina invariantes: remover membership implícita pode ser no-op, enquanto atualizar entidade arquivada continua inválido.

## Budget e localização

Rate limits herdáveis sugerem `BudgetPolicy` separado do provider. O runtime consulta limites efetivos de requests, tokens e categorias de tools.

Local de armazenamento e local de inferência são dimensões diferentes. `storage residency` não é `execution geo`. Configurações imutáveis ou write-once devem ser explícitas.

## Auditoria

Alterações de política, membership ou capacidades devem registrar `actor_ref`, `scope_ref`, operação e resultado no EventLog, independentemente do texto do modelo.

## Consequência para o NetStudio-Codex

A prioridade continua `CLI -> AgentRuntime -> ToolRegistry -> Shell`.

Ao criar o `AgentRuntime`, evitar contexto monolítico:

`ExecutionContext(identity, scope, policy) + MemoryContext + BudgetContext`

Os objetos podem começar pequenos. O importante é não fundir identidade, memória, autorização e orçamento antes de existir necessidade comprovada no runtime.
