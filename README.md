# freebuff-local

Ambiente local para desenvolvimento estilo Cursor/Freebuff, com IA local (llama.cpp + GGUF), editor baseado em Monaco, e backend Node.js com SQLite.

Estrutura criada:

freebuff-local/
├── frontend/ (React + Vite + Monaco + Tailwind + Shadcn UI)
├── backend/ (Node.js + Express + Socket.io + SQLite + integrações Llama)
├── models/ (coloque modelos .gguf aqui)
├── workspace/ (seu espaço de trabalho)
└── docker/

Requisitos mínimos para rodar localmente:

1) Ter Node.js 18+ e npm
2) Clonar o repositório
3) Colocar seu modelo GGUF em models/ (ex: llama-3-8b.gguf)
4) npm install
5) npm run dev

Observações sobre Llama/llama.cpp: O scaffold inclui integrações e scripts auxiliares que esperam que o binário do llama.cpp esteja disponível em backend/llama/bin/llama (ou use build/instalação manual). Veja backend/llama/README.md para instruções detalhadas.

