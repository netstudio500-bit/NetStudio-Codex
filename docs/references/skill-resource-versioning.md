# Referência: skills como recursos versionados

Este documento registra padrões de arquitetura observados em APIs de skills. Não define uma API compatível com provedores externos e não representa implementação existente no NetStudio-Codex.

## Skill não é tool

Uma tool é uma capacidade executável com contrato de entrada e saída. Uma skill é material de comportamento, instrução ou conhecimento que pode orientar um agente. Misturar os dois conceitos torna autorização, carregamento e observabilidade ambíguos.

O futuro `ToolRegistry` deve registrar ferramentas executáveis. Skills, caso adotadas, devem possuir catálogo e ciclo de vida próprios.

## Identidade e versão

Uma skill durável pode ter identidade estável enquanto seu conteúdo evolui por versões. O catálogo pode expor metadados como:

- identificador estável;
- título de exibição separado do conteúdo enviado ao modelo;
- origem do recurso;
- versão mais recente;
- datas de criação e atualização.

Agentes ou execuções reproduzíveis não devem depender implicitamente de `latest`. Quando uma execução precisa ser repetível, a referência deve resolver para uma versão concreta antes do início do runtime.

## Origem e confiança

A origem da skill deve ser explícita. Conteúdo interno, fornecido pelo usuário ou importado de terceiros pode exigir políticas diferentes de validação e confiança.

Origem é metadado de proveniência, não autorização automática. Uma skill marcada como interna ainda precisa passar pelas regras de carregamento e escopo do runtime.

## Exclusão

Exclusão é uma operação destrutiva distinta de leitura e listagem. Uma resposta de remoção deve confirmar a identidade afetada, mas não transforma referências históricas em conteúdo válido.

Antes de permitir remoção física, o NetStudio-Codex deve definir se versões referenciadas por histórico de execução permanecem preservadas, são arquivadas ou tornam a execução não reproduzível.

O mesmo princípio vale para `FileResource`: remover metadata e bytes precisa de política explícita de retenção, referências e auditoria. O modelo não deve receber capacidade destrutiva por padrão.

## Implicação para o NetStudio-Codex

A prioridade atual continua `CLI -> AgentRuntime -> ToolRegistry -> Shell`. Não implementar um `SkillRegistry` antecipadamente.

Quando o runtime possuir contexto de execução e ferramentas reais, avaliar uma abstração interna separada para skills seguindo a direção:

`SkillCatalog -> resolve identity/version -> validate provenance/scope -> attach resolved content to execution context`

Skills não devem ser carregadas por import dinâmico de Python apenas porque a documentação arquitetural antiga usa a palavra "plugin". Conteúdo de orientação e código executável têm riscos e ciclos de vida diferentes.
