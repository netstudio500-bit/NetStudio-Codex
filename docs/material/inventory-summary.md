# Inventário do material de referência

Data de organização: 2026-07-12.

## Resultado

O inventário consolidado recebido registra 89 arquivos e 7 duplicatas exatas. O conjunto é predominantemente documental e reúne referências de APIs, agentes, sessões, ambientes, deployments, memória, ferramentas, Codex e materiais de auditoria do AIInfra.

## Classificação

- `docs/material/`: documentação consolidada e decisões de organização.
- `docs/architecture/`: constituição, arquitetura e RFCs do CODEX NEXT.
- `docs/references/`: referências externas de APIs e fluxos de agentes.
- `docs/audits/`: auditorias e levantamentos históricos do AIInfra.
- `data/inventory/`: inventários tabulares e hashes de integridade.
- `src/`: reservado exclusivamente a código executável do NetStudio-Codex.
- `assets/`: imagens e artefatos visuais não executáveis.

## Duplicatas e material fora de escopo

Duplicatas exatas devem ser preservadas apenas no inventário por SHA-256, sem múltiplas cópias no repositório. Dumps de dependências, binários, credenciais, `.env`, históricos privados e executáveis locais não devem ser incorporados ao Git.

## Critério adotado

O material documental é tratado como referência e não como evidência de funcionalidade implementada. O estado real do código e dos testes do repositório continua sendo a fonte de verdade operacional.
