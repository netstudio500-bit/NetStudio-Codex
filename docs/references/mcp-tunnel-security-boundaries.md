# Referência: fronteiras de segurança para túneis MCP

Este documento registra padrões de segurança observados em APIs de túnel MCP em research preview. Não define suporte a túneis no NetStudio-Codex e não deve ser usado como contrato de compatibilidade com um provedor externo.

## Estado seguro por padrão

Criar um endpoint de conectividade não deve torná-lo operacional imediatamente. O padrão útil é provisionar identidade e endereço primeiro, mantendo tráfego rejeitado até que material de confiança explícito, como certificados de CA, seja configurado.

A direção para integrações remotas é `provision -> establish trust -> enable traffic`, nunca `create -> publicly usable`.

## Operações não idempotentes e retries

Provisionamento que aloca identidade ou hostname novo pode ser não idempotente. O runtime ou uma camada de recovery não deve repetir automaticamente esse tipo de operação após timeout ambíguo.

Operações precisam declarar sua semântica de retry. Uma ação destrutiva ou de provisionamento não pode herdar a mesma política usada para consultas e heartbeats.

## Arquivamento e identidade

Arquivamento irreversível pode invalidar credenciais e arquivar dependências relacionadas em uma única transição. Identidades de rede aposentadas não devem ser recicladas silenciosamente, pois histórico e auditoria precisam continuar distinguindo recursos antigos de novos.

Retries contra um recurso já arquivado podem ser idempotentes quando retornam o estado terminal existente.

## Segredos

Tokens de conexão são credenciais. Consulta de segredo deve ser uma operação sensível separada da leitura de metadata e deve evitar métodos ou superfícies que tendem a registrar valores em URLs e access logs.

O runtime deve transportar referências a segredos sempre que possível. Valores revelados não entram em prompts, memória persistente, histórico de observações ou logs. Redação deve ocorrer antes da persistência, não apenas na apresentação da CLI.

Rotação cria uma nova identidade de credencial e invalida a anterior para novas conexões. Conexões já estabelecidas podem possuir semântica diferente; portanto, `rotate` não deve ser interpretado automaticamente como `disconnect all`.

Motivos de rotação são dados de auditoria e não devem conter o próprio segredo.

## Implicação para o NetStudio-Codex

A prioridade atual continua `CLI -> AgentRuntime -> ToolRegistry -> Shell`. Não implementar túneis MCP agora.

O material é relevante para duas decisões próximas:

1. `ToolRegistry` deve carregar metadata de risco e política, incluindo se uma ferramenta é somente leitura, destrutiva, sensível ou segura para retry automático.
2. O histórico append-only do futuro `AgentRuntime` precisa de uma fronteira de sanitização antes da persistência para impedir gravação de credenciais em decisões, argumentos de tools e observações.

Quando MCP remoto for adotado, conectividade, trust material e secrets devem permanecer fora do loop de decisão do modelo. O agente pode solicitar uma capacidade autorizada; não deve receber token bruto para montar a conexão por conta própria.
