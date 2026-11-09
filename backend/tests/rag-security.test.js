const assert = require('node:assert/strict')
const fs = require('node:fs')
const os = require('node:os')
const path = require('node:path')
const test = require('node:test')

const { indexWorkspace, semanticSearch } = require('../rag/index')

const databaseRows = new Map()
const databaseMetadata = new Map()
let sqliteAvailable = true
try {
  require.resolve('better-sqlite3')
} catch {
  sqliteAvailable = false
}

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
    if (sql.startsWith('SELECT')) {
      return { all: (limit) => this.rows.slice(0, limit) }
    }
    if (sql.startsWith('DELETE')) {
      return { run: () => this.rows.splice(0, this.rows.length) }
    }
    if (sql.startsWith('INSERT OR REPLACE INTO rag_index_metadata')) {
      return { run: (record) => this.metadata.set('workspace_root', record.workspace_root) }
    }
    if (sql.startsWith('INSERT')) {
      return {
        run: (record) => {
          const index = this.rows.findIndex((row) => row.id === record.id)
          if (index >= 0) this.rows.splice(index, 1, record)
          else this.rows.push(record)
        }
      }
    }
    return { run: () => {} }
  }

  transaction(callback) {
    return callback
  }

  close() {}
}

function makeWorkspace() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'netstudio-rag-'))
  const databasePath = path.join(root, 'test-rag.db')
  const workspaceRoot = path.join(root, 'workspace')
  fs.mkdirSync(workspaceRoot)
  return { root, workspaceRoot, databasePath }
}

function options(workspace, extra = {}) {
  return {
    workspaceRoot: workspace.workspaceRoot,
    databasePath: workspace.databasePath,
    Database: MemoryDatabase,
    embedText: async () => [1, 0],
    ...extra
  }
}

test('indexes only authorized text and excludes credential and binary files', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  fs.mkdirSync(path.join(workspace.workspaceRoot, 'docs'))
  const alternateWorkspace = path.join(workspace.root, 'alternate-workspace')
  fs.mkdirSync(alternateWorkspace)
  fs.mkdirSync(path.join(workspace.workspaceRoot, 'secrets'))
  fs.mkdirSync(path.join(workspace.workspaceRoot, '.aws'))
  fs.mkdirSync(path.join(workspace.workspaceRoot, 'node_modules', 'pkg'), { recursive: true })
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'docs', 'guide.md'), 'authorized guide')
  fs.writeFileSync(path.join(workspace.workspaceRoot, '.env'), 'API_TOKEN=private-value-123456')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'token.txt'), 'API_TOKEN=private-value-123456')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'credentials.json'), '{"user":"private"}')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'config.txt'), 'AWS_SECRET_ACCESS_KEY=abcdefghijklmnop')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'settings.md'), 'PASSWORD=short')
  fs.writeFileSync(path.join(workspace.workspaceRoot, '.aws', 'credentials'), '[default]\naws_access_key_id=fixture')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'secrets', 'note.md'), 'private note')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'image.png'), Buffer.from([0, 1, 2]))
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'node_modules', 'pkg', 'readme.md'), 'dependency')

  const result = await indexWorkspace('.', options(workspace))
  const matches = await semanticSearch('guide', { ...options(workspace), k: 10 })
  const otherWorkspaceMatches = await semanticSearch('guide', {
    ...options(workspace),
    workspaceRoot: alternateWorkspace,
    k: 10
  })

  assert.equal(result.indexed, 1)
  assert.equal(matches.length, 1)
  assert.equal(matches[0].file_path, 'docs/guide.md')
  assert.equal(matches[0].snippet, 'authorized guide')
  assert.deepEqual(otherWorkspaceMatches, [])
})

test('rejects absolute paths and traversal outside the workspace', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  const outside = path.join(workspace.root, 'outside')
  fs.mkdirSync(outside)

  await assert.rejects(indexWorkspace(outside, options(workspace)), { code: 'INVALID_PATH' })
  await assert.rejects(indexWorkspace('../outside', options(workspace)), { code: 'INVALID_PATH' })
})

test('does not follow a symlink that escapes the authorized workspace', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  const outside = path.join(workspace.root, 'outside')
  fs.mkdirSync(outside)
  const externalFile = path.join(outside, 'private.md')
  fs.writeFileSync(externalFile, 'external-only-content')
  fs.symlinkSync(outside, path.join(workspace.workspaceRoot, 'external-link'), 'dir')
  const internalDirectory = path.join(workspace.workspaceRoot, 'internal')
  fs.mkdirSync(internalDirectory)
  const internalFile = path.join(internalDirectory, 'allowed.md')
  fs.writeFileSync(internalFile, 'allowed-internal-content')
  fs.symlinkSync(internalDirectory, path.join(workspace.workspaceRoot, 'internal-link'), 'dir')
  fs.symlinkSync(internalFile, path.join(workspace.workspaceRoot, 'internal-file-link.md'))
  const changingDirectory = path.join(workspace.workspaceRoot, 'changing')
  fs.mkdirSync(changingDirectory)
  const parentRaceDirectory = path.join(workspace.workspaceRoot, 'parent-race')
  const movedParentRaceDirectory = path.join(workspace.workspaceRoot, 'parent-race-original')
  fs.mkdirSync(parentRaceDirectory)
  const parentRaceFile = path.join(parentRaceDirectory, 'inside.md')
  fs.writeFileSync(parentRaceFile, 'internal-before-parent-swap')
  let directorySwapped = false
  let parentSwapped = false
  const originalLstatSync = fs.lstatSync
  fs.lstatSync = function (filePath, ...args) {
    if (!parentSwapped && typeof filePath === 'string' && path.resolve(filePath) === parentRaceFile) {
      parentSwapped = true
      fs.renameSync(parentRaceDirectory, movedParentRaceDirectory)
      fs.symlinkSync(outside, parentRaceDirectory, 'dir')
    }
    return originalLstatSync.call(fs, filePath, ...args)
  }
  const raceTarget = path.join(workspace.workspaceRoot, 'race.txt')
  fs.writeFileSync(raceTarget, 'authorized-before-open')
  const originalOpenSync = fs.openSync
  let swapped = false
  fs.openSync = function (filePath, ...args) {
    if (!directorySwapped && typeof filePath === 'string' && path.resolve(filePath) === changingDirectory) {
      directorySwapped = true
      fs.rmdirSync(changingDirectory)
      fs.symlinkSync(outside, changingDirectory, 'dir')
    }
    if (!swapped && typeof filePath === 'string' && path.resolve(filePath) === raceTarget) {
      swapped = true
      fs.unlinkSync(raceTarget)
      fs.symlinkSync(externalFile, raceTarget)
    }
    return originalOpenSync.call(fs, filePath, ...args)
  }

  let result
  try {
    await assert.rejects(indexWorkspace('external-link', options(workspace)), { code: 'INVALID_PATH' })
    result = await indexWorkspace('.', options(workspace))
  } finally {
    fs.lstatSync = originalLstatSync
    fs.openSync = originalOpenSync
  }
  const matches = await semanticSearch('external-only-content', { ...options(workspace), k: 10 })

  assert.equal(swapped, true)
  assert.equal(directorySwapped, true)
  assert.equal(parentSwapped, true)
  assert.equal(result.indexed, 1)
  assert.deepEqual(matches.map((match) => match.file_path), ['internal/allowed.md'])
  assert.equal(matches.some((match) => match.snippet.includes('external-only-content')), false)
})

test('enforces file count, depth, individual size, and total byte limits', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  fs.mkdirSync(path.join(workspace.workspaceRoot, 'nested'))
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'a.txt'), 'A')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'b.txt'), '123456')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'c.txt'), 'C')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'nested', 'deep.txt'), 'D')

  const result = await indexWorkspace('.', options(workspace, {
    maxDepth: 0,
    maxFiles: 2,
    maxFileBytes: 3,
    maxTotalBytes: 4
  }))
  const matches = await semanticSearch('A', { ...options(workspace), k: 10 })

  assert.equal(result.indexed, 1)
  assert.equal(result.skipped, 1)
  assert.equal(result.truncated, true)
  assert.equal(result.bytes_scanned, 1)
  assert.deepEqual(matches.map((match) => match.file_path), ['a.txt'])
})

test('caps the aggregate bytes read across the index operation', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'a.txt'), 'AA')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'b.txt'), 'BB')
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'c.txt'), 'CC')

  const firstFile = path.join(workspace.workspaceRoot, 'a.txt')
  const appendDescriptor = fs.openSync(firstFile, 'a')
  const originalOpenSync = fs.openSync
  let grew = false
  fs.openSync = function (filePath, ...args) {
    if (!grew && typeof filePath === 'string' && path.resolve(filePath) === firstFile) {
      grew = true
      fs.writeSync(appendDescriptor, Buffer.from('more-than-budget'))
    }
    return originalOpenSync.call(fs, filePath, ...args)
  }

  let result
  try {
    result = await indexWorkspace('.', options(workspace, {
      maxFiles: 10,
      maxFileBytes: 20,
      maxTotalBytes: 3
    }))
  } finally {
    fs.openSync = originalOpenSync
    fs.closeSync(appendDescriptor)
  }
  const matches = await semanticSearch('A', { ...options(workspace), k: 10 })

  assert.equal(grew, true)
  assert.equal(result.indexed, 1)
  assert.equal(result.skipped, 2)
  assert.equal(result.truncated, true)
  assert.equal(result.bytes_scanned, 2)
  assert.ok(result.bytes_scanned <= 3)
  assert.deepEqual(matches.map((match) => match.file_path), ['b.txt'])
})

test('caps the total number of directory entries inspected', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  for (const name of ['a.txt', 'b.txt', 'c.txt']) {
    fs.writeFileSync(path.join(workspace.workspaceRoot, name), name)
  }

  const result = await indexWorkspace('.', options(workspace, { maxEntries: 2 }))

  assert.equal(result.indexed, 2)
  assert.equal(result.truncated, true)
})

test('caps search results and rejects invalid or oversized queries', async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  for (let index = 0; index < 14; index += 1) {
    fs.writeFileSync(path.join(workspace.workspaceRoot, `${String(index).padStart(2, '0')}.txt`), 'query marker')
  }

  await indexWorkspace('.', options(workspace, { maxFiles: 20 }))
  const matches = await semanticSearch('query', {
    ...options(workspace),
    k: 100,
    maxResults: 5
  })

  assert.equal(matches.length, 5)
  await assert.rejects(semanticSearch('x'.repeat(513), options(workspace)), { code: 'INVALID_QUERY' })
  await assert.rejects(semanticSearch('query', { ...options(workspace), k: 0 }), { code: 'INVALID_QUERY' })
})

test('persists and searches through SQLite when the native driver is available', {
  skip: !sqliteAvailable
}, async (t) => {
  const workspace = makeWorkspace()
  t.after(() => fs.rmSync(workspace.root, { recursive: true, force: true }))
  fs.writeFileSync(path.join(workspace.workspaceRoot, 'guide.md'), 'sqlite-backed authorized content')

  const configuration = {
    workspaceRoot: workspace.workspaceRoot,
    databasePath: workspace.databasePath,
    embedText: async () => [1, 0]
  }
  const result = await indexWorkspace('.', configuration)
  const matches = await semanticSearch('sqlite-backed', { ...configuration, k: 2 })

  assert.equal(result.indexed, 1)
  assert.equal(matches.length, 1)
  assert.equal(matches[0].snippet, 'sqlite-backed authorized content')
})