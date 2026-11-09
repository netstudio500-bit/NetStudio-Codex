const assert = require('node:assert/strict')
const fs = require('node:fs')
const http = require('node:http')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')

const { createApp, parseAllowedHosts, parseAllowedOrigins } = require('../server')

const projectRoot = path.resolve(__dirname, '../..')
const allowedOrigin = 'http://localhost:5173'
const databaseRows = new Map()
const databaseMetadata = new Map()

class MemoryDatabase {
  constructor(filename) {
    this.filename = path.resolve(filename)
    fs.closeSync(fs.openSync(this.filename, 'a'))
    if (!databaseRows.has(this.filename)) databaseRows.set(this.filename, [])
    if (!databaseMetadata.has(this.filename)) databaseMetadata.set(this.filename, new Map())
    this.rows = databaseRows.get(this.filename)
    this.metadata = databaseMetadata.get(this.filename)
  }

  prepare(sql) {
    if (sql.startsWith('SELECT value FROM rag_index_metadata')) {
      return { get: () => ({ value: this.metadata.get('workspace_root') }) }
    }
    if (sql.startsWith('SELECT')) return { all: (limit) => this.rows.slice(0, limit) }
    if (sql.startsWith('DELETE')) return { run: () => this.rows.splice(0, this.rows.length) }
    if (sql.startsWith('INSERT OR REPLACE INTO rag_index_metadata')) {
      return { run: (record) => this.metadata.set('workspace_root', record.workspace_root) }
    }
    if (sql.startsWith('INSERT')) {
      return { run: (record) => this.rows.push(record) }
    }
    return { run: () => {} }
  }

  transaction(callback) {
    return callback
  }

  close() {}
}

async function startTestServer(t, app) {
  const server = app.listen(0, '127.0.0.1')
  await new Promise((resolve, reject) => {
    server.once('listening', resolve)
    server.once('error', reject)
  })
  t.after(() => new Promise((resolve) => server.close(resolve)))
  return `http://127.0.0.1:${server.address().port}`
}

function requestWithHost(url, host) {
  return new Promise((resolve, reject) => {
    const request = http.request(url, { headers: { Host: host } }, (response) => {
      let body = ''
      response.setEncoding('utf8')
      response.on('data', (chunk) => { body += chunk })
      response.on('end', () => resolve({ status: response.statusCode, body: JSON.parse(body) }))
    })
    request.on('error', reject)
    request.end()
  })
}

test('allows the frontend origin and keeps RAG inside the configured workspace', async (t) => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'netstudio-http-'))
  const workspaceRoot = path.join(root, 'workspace')
  fs.mkdirSync(workspaceRoot)
  fs.writeFileSync(path.join(workspaceRoot, 'guide.md'), 'authorized workspace content')
  const outsideRoot = path.join(root, 'outside')
  fs.mkdirSync(outsideRoot)
  fs.writeFileSync(path.join(outsideRoot, 'private.md'), 'must never be indexed')
  let releaseEmbedding
  let signalEmbeddingStarted
  const embeddingStarted = new Promise((resolve) => { signalEmbeddingStarted = resolve })
  const embeddingGate = new Promise((resolve) => { releaseEmbedding = resolve })
  const app = createApp({
    workspaceRoot,
    allowedOrigins: [allowedOrigin, 'http://127.0.0.1:5173'],
    ragOptions: {
      databasePath: path.join(root, 'rag-secure-v1.db'),
      Database: MemoryDatabase,
      embedText: async () => {
        signalEmbeddingStarted()
        await embeddingGate
        return [1, 0]
      }
    }
  })
  const baseUrl = await startTestServer(t, app)
  t.after(() => fs.rmSync(root, { recursive: true, force: true }))

  const indexingRequest = fetch(`${baseUrl}/api/rag/index`, {
    method: 'POST',
    headers: { Origin: allowedOrigin, 'Content-Type': 'application/json' },
    body: '{}'
  })
  await embeddingStarted
  try {
    const concurrentIndex = await fetch(`${baseUrl}/api/rag/index`, {
      method: 'POST',
      headers: { Origin: allowedOrigin, 'Content-Type': 'application/json' },
      body: '{}'
    })
    assert.equal(concurrentIndex.status, 429)
    assert.equal((await concurrentIndex.json()).error, 'RAG indexing is already in progress')
  } finally {
    releaseEmbedding()
  }
  const indexed = await indexingRequest
  const indexBody = await indexed.json()
  assert.equal(indexed.status, 200)
  assert.equal(indexed.headers.get('access-control-allow-origin'), allowedOrigin)
  assert.equal(indexBody.result.indexed, 1)
  assert.equal(JSON.stringify(indexBody).includes(workspaceRoot), false)

  const searched = await fetch(`${baseUrl}/api/rag/search`, {
    method: 'POST',
    headers: { Origin: allowedOrigin, 'Content-Type': 'application/json' },
    body: JSON.stringify({ query: 'authorized workspace', k: 5 })
  })
  const searchBody = await searched.json()
  assert.equal(searched.status, 200)
  assert.equal(searchBody.results.length, 1)
  assert.equal(searchBody.results[0].file_path, 'guide.md')
  assert.equal(searchBody.results[0].snippet, 'authorized workspace content')

  const deniedOrigin = await fetch(`${baseUrl}/api/rag/index`, {
    method: 'POST',
    headers: { Origin: 'https://untrusted.example', 'Content-Type': 'application/json' },
    body: JSON.stringify({ root: outsideRoot })
  })
  assert.equal(deniedOrigin.status, 403)
  assert.equal(deniedOrigin.headers.get('access-control-allow-origin'), null)
  assert.equal((await deniedOrigin.json()).error, 'Origin not allowed')

  const traversal = await fetch(`${baseUrl}/api/rag/index`, {
    method: 'POST',
    headers: { Origin: allowedOrigin, 'Content-Type': 'application/json' },
    body: JSON.stringify({ root: '../outside' })
  })
  const traversalBody = await traversal.json()
  assert.equal(traversal.status, 400)
  assert.equal(traversalBody.error, 'Invalid RAG request')
  assert.equal(JSON.stringify(traversalBody).includes(root), false)

  const invalidHost = await requestWithHost(`${baseUrl}/api/health`, 'rebind.attacker.example')
  assert.equal(invalidHost.status, 400)
  assert.equal(invalidHost.body.error, 'Host not allowed')
  const userInfoHost = await requestWithHost(`${baseUrl}/api/health`, 'attacker@localhost')
  assert.equal(userInfoHost.status, 400)
  assert.equal(userInfoHost.body.error, 'Host not allowed')
})

test('rejects wildcard and invalid CORS configuration', () => {
  assert.throws(() => parseAllowedOrigins('*'), /explicit origins/)
  assert.throws(() => parseAllowedOrigins('not-an-origin'), /invalid origin/)
  assert.deepEqual([...parseAllowedOrigins([allowedOrigin])], [allowedOrigin])
  assert.throws(() => parseAllowedHosts('*'), /explicit hostnames/)
  assert.deepEqual([...parseAllowedHosts(['backend'])], ['backend'])
})

test('publishes Ollama only on host loopback while retaining internal service access', () => {
  const compose = fs.readFileSync(path.join(projectRoot, 'docker-compose.yml'), 'utf8')
  assert.match(compose, /127\.0\.0\.1:11434:11434/)
  assert.match(compose, /OLLAMA_HOST=0\.0\.0\.0:11434/)
  assert.match(compose, /OLLAMA_BASE_URL=http:\/\/ollama:11434/)
  assert.match(compose, /127\.0\.0\.1:8000:8000/)
  assert.match(compose, /127\.0\.0\.1:8001:8001/)
})

test('publishes Node services locally and mounts the authorized workspace read-only', () => {
  const compose = fs.readFileSync(path.join(projectRoot, 'docker', 'docker-compose.yml'), 'utf8')
  assert.match(compose, /127\.0\.0\.1:5173:5173/)
  assert.match(compose, /127\.0\.0\.1:5174:5174/)
  assert.match(compose, /HOST=0\.0\.0\.0/)
  assert.match(compose, /WORKSPACE_ROOT=\/workspace/)
  assert.match(compose, /ALLOWED_HOSTS=localhost,127\.0\.0\.1,\[::1\],backend/)
  assert.match(compose, /\.\.\/workspace:\/workspace:ro/)
  assert.match(compose, /HOST=0\.0\.0\.0/)
  assert.match(compose, /context: \.\./)
})