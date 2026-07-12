# Referência: ciclo de vida de recursos de arquivo

Este documento registra padrões úteis observados em APIs de upload de arquivos. Não define uma API HTTP para o NetStudio-Codex e não representa implementação existente.

## Metadados mínimos

Um recurso de arquivo deve poder ser descrito sem depender do caminho físico original. Metadados úteis incluem:

- identificador interno estável;
- nome original do arquivo;
- MIME type;
- tamanho em bytes;
- instante de criação;
- política de acesso, como disponibilidade para download;
- escopo opcional de propriedade ou sessão.

O formato externo de IDs não deve ser assumido como contrato permanente.

## Arquivo não é caminho

O runtime não deve transportar caminhos arbitrários como identidade durável de um arquivo. O upload ou ingestão produz um recurso identificado; a resolução desse recurso para armazenamento ou `mount_path` pertence à camada de workspace/resource management.

Isso reduz acoplamento entre CLI, sessão, ferramentas e layout do filesystem local.

## Escopo

Recursos podem ser globais ao workspace ou vinculados a uma sessão. O escopo deve ser explícito quando existir. Encerrar uma sessão não implica apagar silenciosamente recursos duráveis; retenção e remoção precisam de política própria.

## Implicação para o NetStudio-Codex

A documentação arquitetural atual cita `workspace/files.py`, mas essa capacidade ainda não deve ser tratada como implementada. Quando o loop de ferramentas exigir leitura e escrita de arquivos, introduzir uma abstração interna de recurso antes de criar upload HTTP ou UI.

A direção recomendada é:

`filesystem input -> ingestão/validação -> FileResource metadata -> workspace storage -> tool resolution`

Validação de tamanho, MIME type e acesso deve ocorrer na fronteira de ingestão. Ferramentas recebem referências resolvidas pelo runtime/workspace, evitando que o modelo escolha livremente caminhos fora do escopo permitido.
