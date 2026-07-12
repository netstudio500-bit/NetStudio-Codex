# Mapa de referência: Managed Agents

Este documento organiza o material de API recebido como referência de arquitetura. Ele não representa implementação automática no NetStudio-Codex.

## Ambientes

Ambientes definem execução `cloud` ou `self_hosted`. Em cloud, a configuração pode declarar política de rede e pacotes de `apt`, `cargo`, `gem`, `go`, `npm` e `pip`.

Operações documentadas: obter, atualizar, arquivar e excluir ambiente.

## Work items self-hosted

O worker pré-construído normalmente orquestra o ciclo de work items. O fluxo de referência é:

`poll -> ack -> heartbeat -> active -> stop/stopped`

Há endpoints de consulta individual, listagem, estatísticas de fila e atualização de metadata. Heartbeats usam lease e podem aplicar concorrência otimista por `expected_last_heartbeat`.

## Sessões e recursos

Sessões podem receber recursos de arquivo, repositório GitHub e memory store. Recursos possuem `mount_path` quando aplicável. Recursos GitHub suportam rotação de token de autorização; recursos podem ser consultados, listados e removidos.

## Deployments

Deployments podem iniciar execuções e produzir registros append-only de `deployment_run`. Uma execução registra `session_id` em sucesso ou um erro tipado em falha. Entre os erros documentados estão ambiente ou agente arquivado, recurso ausente, rate limit, bloqueio de egress MCP e incompatibilidade de recursos com ambiente self-hosted.

A listagem de runs usa paginação por cursor opaco e permite filtros temporais, por deployment, tipo de gatilho e presença de erro. O contrato mantém a invariável de resultado: exatamente um entre `session_id` e `error` deve estar preenchido.

Os erros de criação de sessão formam uma taxonomia útil para recovery: recurso ausente ou arquivado, organização desabilitada, rate limit, rejeição de validação, incompatibilidade de recursos self-hosted, bloqueio de egress MCP e falha desconhecida. Essa classificação é referência para distinguir falhas recuperáveis de falhas permanentes, sem importar os tipos externos para o core.

## Implicação para o NetStudio-Codex

O padrão útil é separar configuração durável, sessão stateful, recursos montáveis, unidade de trabalho e registro de execução. A adoção deve ser feita por RFC e testes, evitando copiar contratos externos diretamente para o core local.

Para o futuro `AgentRuntime`, o material reforça três decisões: histórico de execução append-only, estado terminal mutuamente exclusivo entre sucesso e erro e erros classificados por política de retry/recovery. Paginação e filtros pertencem à camada de consulta do histórico, não ao loop de decisão do agente.
