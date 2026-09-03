# llama.cpp integration

This folder contains a small bridge to call a compiled llama.cpp binary in a CLI form.

Usage:

1. Build llama.cpp on your machine following the official repo: https://github.com/ggerganov/llama.cpp
2. Copy the built binary into backend/llama/bin/ (e.g. backend/llama/bin/llama)
3. Place your GGUF model in /models (ex: models/llama-3-8b.gguf)
4. Start the backend and call POST /api/chat with {message: 'Olá'}

Notes:
- The provided llama.js wrapper is intentionally minimal. For better performance consider using an IPC/ffi approach or a native Node binding.
