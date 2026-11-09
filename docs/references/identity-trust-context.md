# Referência: identidade, perfil e contexto de confiança

Este documento registra padrões observados em APIs de perfil de usuário. Não define suporte a perfis externos no NetStudio-Codex e não representa implementação existente.

## Identidade não é memória

Um perfil identifica a entidade em nome da qual uma execução ocorre. Memória registra fatos ou contexto persistido. Misturar os dois conceitos cria risco de usar conteúdo lembrado como prova de identidade ou autorização.

O futuro `AgentRuntime` deve receber um contexto de execução com identidade resolvida separadamente do contexto de memória.

## Identificador interno e referência externa

A identidade interna deve possuir identificador próprio. Um `external_id` fornecido por outra plataforma é correlação, não chave primária nem prova de unicidade. O runtime não deve presumir que duas referências externas iguais representam necessariamente a mesma entidade sem política explícita do adaptador de identidade.

Nome de exibição também não é identidade nem autorização.

## Metadata limitada e validada

Metadata livre deve possuir limites de quantidade e tamanho e aceitar somente valores simples quando usada em fronteiras de runtime. Isso reduz crescimento sem controle, serialização ambígua e uso de metadata como depósito informal de prompts, segredos ou memória.

Atualizações parciais precisam ter semântica explícita de merge e remoção. Ausência de chave, valor vazio e `null` não devem adquirir significados diferentes por acidente entre providers.

## Relação e confiança

A relação da entidade com a plataforma é contexto de proveniência. Estados de confiança são dados separados e podem ser `pending`, `active` ou `rejected`.

Confiança não deve ser reduzida a um booleano genérico e não deve ser inferida da origem, nome ou relação. Uma capacidade sensível deve consultar uma concessão específica e seu estado atual.

O modelo pode receber apenas a conclusão de política necessária para decidir entre capacidades disponíveis. Detalhes administrativos de grants não precisam entrar no prompt.

## Enrollment e links efêmeros

URLs de enrollment são artefatos temporários com expiração. Devem ser tratadas como material sensível de fluxo de identidade: não entram em memória, histórico append-only ou observações de tools persistidas sem sanitização.

Criação de enrollment é uma operação administrativa separada do loop do agente e não deve ser exposta como tool padrão.

## Implicação para o NetStudio-Codex

A prioridade permanece `CLI -> AgentRuntime -> ToolRegistry -> Shell`.

Ao introduzir `AgentRuntime`, o contexto mínimo deve permitir evolução futura sem acoplar memória à identidade. A direção é:

`ExecutionContext(identity_ref?, session_ref?, policy context) + MemoryContext`

O `ToolRegistry` futuro poderá filtrar capacidades por política resolvida antes de apresentá-las ao modelo. O agente escolhe entre tools autorizadas; ele não interpreta grants administrativos nem promove seu próprio nível de confiança.

Não implementar `UserProfile` agora. O valor deste material é preservar a fronteira entre identidade, memória e autorização antes que o runtime persistente seja criado.
