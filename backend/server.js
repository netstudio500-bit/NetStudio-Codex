const express = require('express')
const http = require('http')
const { Server } = require('socket.io')
const path = require('path')
const cors = require('cors')
const ll = require('./llama/llama')
const rag = require('./rag/index')

const DEFAULT_ALLOWED_ORIGINS = [
  'http://localhost:5173',
  'http://127.0.0.1:5173'
]
const DEFAULT_ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

function parseAllowedOrigins(value = process.env.ALLOWED_ORIGINS) {
  const values = Array.isArray(value)
    ? value
    : (value || DEFAULT_ALLOWED_ORIGINS.join(',')).split(',')
  const origins = new Set()
  for (const candidate of values) {
    const origin = String(candidate).trim()
    if (!origin || origin === '*') throw new Error('ALLOWED_ORIGINS must contain explicit origins')
    let parsed
    try {
      parsed = new URL(origin)
    } catch {
      throw new Error('ALLOWED_ORIGINS contains an invalid origin')
    }
    if (!['http:', 'https:'].includes(parsed.protocol) || parsed.origin !== origin ||
        parsed.username || parsed.password) {
      throw new Error('ALLOWED_ORIGINS contains an invalid origin')
    }
    origins.add(origin)
  }
  if (origins.size === 0) throw new Error('ALLOWED_ORIGINS cannot be empty')
  return origins
}

function parseAllowedHosts(value = process.env.ALLOWED_HOSTS) {
  const values = Array.isArray(value)
    ? value
    : (value || DEFAULT_ALLOWED_HOSTS.join(',')).split(',')
  const hosts = new Set()
  for (const candidate of values) {
    const host = String(candidate).trim().toLowerCase()
    if (!host || host === '*') throw new Error('ALLOWED_HOSTS must contain explicit hostnames')
    let parsed
    try {
      parsed = new URL(`http://${host}`)
    } catch {
      throw new Error('ALLOWED_HOSTS contains an invalid hostname')
    }
    if (parsed.hostname !== host || parsed.username || parsed.password || parsed.port ||
        parsed.pathname !== '/') {
      throw new Error('ALLOWED_HOSTS contains an invalid hostname')
    }
    hosts.add(host)
  }
  if (hosts.size === 0) throw new Error('ALLOWED_HOSTS cannot be empty')
  return hosts
}

function isAllowedHostHeader(hostHeader, allowedHosts) {
  try {
    const parsedHost = new URL(`http://${hostHeader}`)
    return !parsedHost.username && !parsedHost.password && parsedHost.pathname === '/' &&
      !parsedHost.search && !parsedHost.hash && allowedHosts.has(parsedHost.hostname.toLowerCase())
  } catch {
    return false
  }
}

function configuredWorkspaceRoot() {
  const configured = process.env.WORKSPACE_ROOT || path.join(__dirname, '..', 'workspace')
  return path.resolve(__dirname, '..', configured)
}

function createApp(options = {}) {
  const ragService = options.ragService || rag
  const workspaceRoot = ragService.resolveWorkspaceRoot(
    options.workspaceRoot || configuredWorkspaceRoot()
  )
  const allowedOrigins = parseAllowedOrigins(options.allowedOrigins)
  const allowedHosts = parseAllowedHosts(options.allowedHosts)
  const ragOptions = { ...(options.ragOptions || {}), workspaceRoot }
  const app = express()
  let indexing = false

  app.disable('x-powered-by')
  app.use((req, res, next) => {
    const hostHeader = req.get('Host')
    if (!isAllowedHostHeader(hostHeader, allowedHosts)) {
      return res.status(400).json({ error: 'Host not allowed' })
    }
    const origin = req.get('Origin')
    if (origin && !allowedOrigins.has(origin)) {
      return res.status(403).json({ error: 'Origin not allowed' })
    }
    return next()
  })
  app.use(cors({
    origin: (origin, callback) => callback(null, Boolean(origin && allowedOrigins.has(origin))),
    methods: ['GET', 'POST', 'OPTIONS'],
    optionsSuccessStatus: 204
  }))
  app.use(express.json({ limit: '16kb' }))

  app.get('/api/health', (req, res) => res.json({ ok: true }))

  app.get('/api/files', (req, res) => {
    res.json({ files: ['/workspace/project/main.py', '/workspace/project/README.md'] })
  })

  app.post('/api/chat', async (req, res) => {
    const message = req.body && req.body.message
    if (typeof message !== 'string' || !message.trim() || message.length > 16000) {
      return res.status(400).json({ error: 'Invalid chat request' })
    }
    try {
      const reply = await ll.query({ message })
      return res.json({ reply })
    } catch {
      return res.status(500).json({ error: 'Chat request failed' })
    }
  })

  app.post('/api/rag/index', async (req, res) => {
    if (indexing) return res.status(429).json({ error: 'RAG indexing is already in progress' })
    indexing = true
    try {
      const requestedRoot = req.body && req.body.root !== undefined ? req.body.root : '.'
      const result = await ragService.indexWorkspace(requestedRoot, ragOptions)
      return res.json({ ok: true, result })
    } catch (error) {
      const status = error && error.code === 'WORKSPACE_UNAVAILABLE' ? 503
        : error && error.name === 'RagInputError' ? 400 : 500
      return res.status(status).json({
        error: status === 400 ? 'Invalid RAG request' : 'RAG indexing failed'
      })
    } finally {
      indexing = false
    }
  })

  app.post('/api/rag/search', async (req, res) => {
    try {
      const query = req.body && req.body.query
      const k = req.body && req.body.k !== undefined ? req.body.k : rag.DEFAULT_MAX_RESULTS
      const results = await ragService.semanticSearch(query, { ...ragOptions, k })
      return res.json({ ok: true, results })
    } catch (error) {
      const status = error && error.name === 'RagInputError' ? 400 : 500
      return res.status(status).json({
        error: status === 400 ? 'Invalid RAG request' : 'RAG search failed'
      })
    }
  })

  app.use((error, req, res, next) => {
    if (res.headersSent) return next(error)
    return res.status(400).json({ error: 'Invalid request' })
  })
  return app
}

function startServer() {
  const initDb = require('./database/init')
  initDb(path.join(__dirname, 'data', 'freebuff.db'))
  const app = createApp()
  const server = http.createServer(app)
  const allowedOrigins = [...parseAllowedOrigins()]
  const allowedHosts = [...parseAllowedHosts()]
  const io = new Server(server, {
    cors: { origin: allowedOrigins, methods: ['GET', 'POST'] },
    allowRequest: (request, callback) => {
      const origin = request.headers.origin
      callback(
        null,
        isAllowedHostHeader(request.headers.host, new Set(allowedHosts)) &&
          (!origin || allowedOrigins.includes(origin))
      )
    }
  })

  io.on('connection', (socket) => {
    socket.on('chat:message', async (payload) => {
      const message = payload && payload.message
      if (typeof message !== 'string' || !message.trim() || message.length > 16000) {
        socket.emit('chat:error', { error: 'Invalid chat request' })
        return
      }
      try {
        const reply = await ll.query({ message })
        socket.emit('chat:reply', { reply })
      } catch {
        socket.emit('chat:error', { error: 'Chat request failed' })
      }
    })
  })

  const port = Number(process.env.PORT || 5174)
  const host = process.env.HOST || '127.0.0.1'
  server.listen(port, host, () => console.log(`Backend running on ${host}:${port}`))
  return { app, io, server }
}

if (require.main === module) startServer()

module.exports = {
  createApp,
  parseAllowedOrigins,
  parseAllowedHosts,
  isAllowedHostHeader,
  startServer
}
