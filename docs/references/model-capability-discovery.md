# Referência: descoberta de modelos por capacidade

Este documento registra um padrão de arquitetura observado em APIs de modelos. Não define compatibilidade com provedores externos nem autoriza copiar seus contratos para o core.

## Problema observado

O contrato atual de `LLMProvider.list_models()` retorna apenas `list[str]`. Isso permite descobrir identificadores, mas não permite ao runtime decidir se um modelo suporta uma necessidade concreta antes da execução.

Exemplos de capacidades relevantes para um agente local incluem entrada de imagem ou PDF, saída estruturada, execução de código, modos de raciocínio, gerenciamento de contexto e limites de entrada e saída.

## Padrão útil

A descoberta de modelos pode retornar descritores com:

- identificador estável e nome de exibição;
- limites de contexto e geração;
- conjunto explícito de capacidades suportadas;
- relações de fallback permitidas quando o provider realmente oferece essa semântica.

Capacidades devem ser consultáveis como dados. O runtime não deve inferir suporte pelo nome do modelo nem manter listas mágicas espalhadas pelo código.

## Implicação para o NetStudio-Codex

Não alterar `LLMProvider` durante a fase atual apenas para reproduzir uma API externa. A prioridade continua sendo `CLI -> AgentRuntime -> ToolRegistry -> Shell`.

Quando o `AgentRuntime` precisar selecionar modelo ou validar requisitos de ferramenta, evoluir a abstração com um tipo interno como `ModelDescriptor` e capacidades normalizadas pelo provider. `OllamaProvider` deverá preencher somente informações que consiga descobrir ou declarar com segurança; capacidade desconhecida deve permanecer desconhecida, nunca ser convertida silenciosamente em `False`.

A seleção futura deve seguir a direção `requisitos da execução -> capacidades declaradas -> modelos elegíveis`. Fallback é política separada da descoberta e não deve ficar embutido no loop de decisão do agente.
