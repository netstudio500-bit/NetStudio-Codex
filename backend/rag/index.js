const fs = require('fs')
const path = require('path')
const Embeddings = require('./embeddings')

const DEFAULT_MAX_DEPTH = 12
const DEFAULT_MAX_FILES = 1000
const DEFAULT_MAX_ENTRIES = 10000
const DEFAULT_MAX_FILE_BYTES = 1024 * 1024
const DEFAULT_MAX_TOTAL_BYTES = 20 * 1024 * 1024
const DEFAULT_MAX_RESULTS = 10
const MAX_QUERY_CHARS = 512
const MAX_SNIPPET_CHARS = 4000
const DEFAULT_WORKSPACE_ROOT = path.resolve(__dirname, '..', '..', 'workspace')
const DEFAULT_DATABASE_PATH = process.env.RAG_DATABASE_PATH ||
  path.join(__dirname, '..', 'data', 'rag-secure-v1.db')

const EXCLUDED_DIRECTORIES = new Set([
  '.git', '.hg', '.svn', '.netstudio', 'node_modules', '.venv', 'venv',
  '__pycache__', 'dist', 'build', '.next', '.cache', 'coverage', 'models',
  '.aws', '.azure', '.docker', '.gnupg', '.kube', '.ssh'
])
const EXCLUDED_FILES = new Set([
  '.npmrc', '.pypirc', '.netrc', 'credentials', 'secrets', 'secrets.json',
  '.dockerconfigjson', 'id_rsa', 'id_ed25519', 'authorized_keys', 'known_hosts'
])
const SENSITIVE_FILE_NAME = /(^|[._-])(credential|credentials|secret|secrets|token|tokens)([._-]|$)/i
const EXCLUDED_EXTENSIONS = new Set([
  '.pem', '.key', '.p12', '.pfx', '.jks', '.keystore', '.crt', '.cer', '.der',
  '.db', '.sqlite', '.sqlite3', '.png', '.jpg', '.jpeg', '.gif', '.webp',
  '.exe', '.dll', '.so', '.dylib', '.bin', '.gguf', '.zip', '.gz', '.tar',
  '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
])
const SENSITIVE_CONTENT = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/i,
  /\b[A-Z0-9_]*(?:API[_-]?(?:KEY|TOKEN)|ACCESS[_-]?TOKEN|AUTH[_-]?TOKEN|CLIENT[_-]?SECRET|PASSWORD|PASSWD|SECRET|TOKEN|PRIVATE[_-]?KEY)[A-Z0-9_]*\b\s*[:=]\s*(?!\$\{|\{)(?:"[^"\r\n]+"|'[^'\r\n]+'|[^\s,;#]+)/i,
  /\bAKIA[0-9A-Z]{16}\b/,
  /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/
]

class RagInputError extends Error {
  constructor(code, message) {
    super(message)
    this.name = 'RagInputError'
    this.code = code
  }
}

function isWithin(root, candidate) {
  const relative = path.relative(root, candidate)
  return relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))
}

function resolveWorkspaceRoot(workspaceRoot = DEFAULT_WORKSPACE_ROOT) {
  let canonical
  try {
    canonical = fs.realpathSync(workspaceRoot)
  } catch {
    throw new RagInputError('WORKSPACE_UNAVAILABLE', 'Authorized workspace is unavailable')
  }
  if (!fs.statSync(canonical).isDirectory()) {
    throw new RagInputError('WORKSPACE_UNAVAILABLE', 'Authorized workspace is unavailable')
  }
  return canonical
}

function resolveRequestedRoot(requestedRoot, workspaceRoot) {
  if (typeof requestedRoot !== 'string' || !requestedRoot.trim() || requestedRoot.includes('\0')) {
    throw new RagInputError('INVALID_PATH', 'Invalid workspace path')
  }
  const normalized = requestedRoot.replace(/\\/g, '/')
  if (path.isAbsolute(requestedRoot) || path.win32.isAbsolute(requestedRoot) || /^[a-zA-Z]:/.test(requestedRoot)) {
    throw new RagInputError('INVALID_PATH', 'Only relative workspace paths are allowed')
  }
  if (normalized.split('/').includes('..')) {
    throw new RagInputError('INVALID_PATH', 'Path traversal is not allowed')
  }

  let canonical
  try {
    canonical = fs.realpathSync(path.resolve(workspaceRoot, normalized))
  } catch {
    throw new RagInputError('INVALID_PATH', 'Workspace path does not exist')
  }
  if (!isWithin(workspaceRoot, canonical)) {
    throw new RagInputError('INVALID_PATH', 'Path is outside the authorized workspace')
  }
  try {
    if (!fs.statSync(canonical).isDirectory()) {
      throw new RagInputError('INVALID_PATH', 'Workspace path is not a directory')
    }
  } catch (error) {
    if (error instanceof RagInputError) throw error
    throw new RagInputError('INVALID_PATH', 'Workspace path is unavailable')
  }
  return canonical
}

function isExcludedPath(filePath, isDirectory) {
  const name = path.basename(filePath).toLowerCase()
  if (isDirectory && (EXCLUDED_DIRECTORIES.has(name) || SENSITIVE_FILE_NAME.test(name))) return true
  if (!isDirectory && (EXCLUDED_FILES.has(name) || name === '.env' || name.startsWith('.env.') ||
      SENSITIVE_FILE_NAME.test(name))) {
    return true
  }
  return !isDirectory && EXCLUDED_EXTENSIONS.has(path.extname(name))
}

function readDirectoryEntries(directory, workspaceRoot, maxEntries) {
  if (process.platform === 'linux') {
    let descriptor
    let handle
    try {
      descriptor = fs.openSync(
        directory,
        fs.constants.O_RDONLY | fs.constants.O_DIRECTORY | fs.constants.O_NOFOLLOW
      )
      const descriptorPath = `/proc/self/fd/${descriptor}`
      const canonical = fs.realpathSync(descriptorPath)
      if (!fs.fstatSync(descriptor).isDirectory() || !isWithin(workspaceRoot, canonical)) {
        return { entries: [], skipped: true, truncated: false }
      }
      handle = fs.opendirSync(descriptorPath)
      const entries = []
      while (entries.length < maxEntries) {
        const entry = handle.readSync()
        if (!entry) break
        entries.push(entry)
      }
      const hasMoreEntries = handle.readSync() !== null
      return {
        entries,
        skipped: false,
        truncated: hasMoreEntries
      }
    } catch {
      return { entries: [], skipped: true, truncated: false }
    } finally {
      if (handle) handle.closeSync()
      if (descriptor !== undefined) fs.closeSync(descriptor)
    }
  }

  let handle
  try {
    const canonical = fs.realpathSync(directory)
    const beforeOpen = fs.lstatSync(directory)
    if (!isWithin(workspaceRoot, canonical) || !beforeOpen.isDirectory() || beforeOpen.isSymbolicLink()) {
      return { entries: [], skipped: true, truncated: false }
    }
    handle = fs.opendirSync(directory)
    const afterOpen = fs.lstatSync(directory)
    if (afterOpen.isSymbolicLink() || beforeOpen.dev !== afterOpen.dev || beforeOpen.ino !== afterOpen.ino) {
      return { entries: [], skipped: true, truncated: false }
    }
    const entries = []
    while (entries.length < maxEntries) {
      const entry = handle.readSync()
      if (!entry) break
      entries.push(entry)
    }
    return { entries, skipped: false, truncated: handle.readSync() !== null }
  } catch {
    return { entries: [], skipped: true, truncated: false }
  } finally {
    if (handle) handle.closeSync()
  }
}

function collectFiles(root, maxDepth, maxFiles, maxEntries) {
  const files = []
  let truncated = false
  let entriesVisited = 0

  function visit(directory, depth) {
    const remainingEntries = maxEntries - entriesVisited
    if (remainingEntries <= 0) {
      truncated = true
      return
    }
    const directoryResult = readDirectoryEntries(directory, root, remainingEntries)
    if (directoryResult.skipped) {
      truncated = true
      return
    }
    const entries = directoryResult.entries
    entriesVisited += entries.length
    if (directoryResult.truncated) truncated = true
    entries.sort((left, right) => left.name.localeCompare(right.name))
    for (const entry of entries) {
      const fullPath = path.join(directory, entry.name)
      if (entry.isSymbolicLink() || isExcludedPath(fullPath, entry.isDirectory())) continue
      if (entry.isDirectory()) {
        if (depth >= maxDepth) {
          truncated = true
          continue
        }
        visit(fullPath, depth + 1)
      } else if (entry.isFile() && !isExcludedPath(fullPath, false)) {
        if (files.length >= maxFiles) {
          truncated = true
          return
        }
        files.push(fullPath)
      }
      if (truncated && files.length >= maxFiles) return
    }
    if (directoryResult.truncated) return
  }

  visit(root, 0)
  return { files, truncated }
}

function readSafeText(filePath, workspaceRoot, maxFileBytes, maxReadBytes) {
  let descriptor
  let bytesRead = 0
  try {
    const canonical = fs.realpathSync(filePath)
    if (!isWithin(workspaceRoot, canonical)) return { skipped: 'unsafe' }
    const beforeOpen = fs.lstatSync(filePath)
    if (!beforeOpen.isFile() || beforeOpen.isSymbolicLink()) return { skipped: 'unsafe' }
    if (beforeOpen.size > maxFileBytes) return { skipped: 'too_large' }
    if (beforeOpen.size > maxReadBytes) return { skipped: 'total_limit' }

    const noFollow = fs.constants.O_NOFOLLOW || 0
    descriptor = fs.openSync(filePath, fs.constants.O_RDONLY | noFollow)
    const opened = fs.fstatSync(descriptor)
    if (!opened.isFile() || opened.dev !== beforeOpen.dev || opened.ino !== beforeOpen.ino) {
      return { skipped: 'unsafe' }
    }
    const openedCanonical = process.platform === 'linux'
      ? fs.realpathSync(`/proc/self/fd/${descriptor}`)
      : fs.realpathSync(filePath)
    if (!isWithin(workspaceRoot, openedCanonical)) return { skipped: 'unsafe' }
    if (opened.size > maxFileBytes) return { skipped: 'too_large' }
    if (opened.size > maxReadBytes) return { skipped: 'total_limit' }

    const readLimit = Math.min(maxFileBytes, maxReadBytes)
    const buffer = Buffer.alloc(readLimit)
    while (bytesRead < buffer.length) {
      const count = fs.readSync(descriptor, buffer, bytesRead, buffer.length - bytesRead, null)
      if (count === 0) break
      bytesRead += count
    }
    const afterRead = fs.fstatSync(descriptor)
    if (afterRead.size > bytesRead) {
      return {
        skipped: afterRead.size > maxFileBytes ? 'too_large' : 'total_limit',
        bytesRead
      }
    }

    let content
    try {
      content = new TextDecoder('utf-8', { fatal: true }).decode(buffer.subarray(0, bytesRead))
    } catch {
      return { skipped: 'binary', bytesRead }
    }
    if (/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/.test(content)) {
      return { skipped: 'binary', bytesRead }
    }
    if (SENSITIVE_CONTENT.some((pattern) => pattern.test(content))) {
      return { skipped: 'sensitive', bytesRead }
    }
    return { content, bytesRead }
  } catch {
    return { skipped: 'unavailable', bytesRead }
  } finally {
    if (descriptor !== undefined) fs.closeSync(descriptor)
  }
}

function databaseConstructor(options) {
  return options.Database || require('better-sqlite3')
}

async function indexWorkspace(requestedRoot = '.', options = {}) {
  const workspaceRoot = resolveWorkspaceRoot(options.workspaceRoot)
  const root = resolveRequestedRoot(requestedRoot, workspaceRoot)
  const maxDepth = options.maxDepth ?? DEFAULT_MAX_DEPTH
  const maxFiles = options.maxFiles ?? DEFAULT_MAX_FILES
  const maxEntries = options.maxEntries ?? DEFAULT_MAX_ENTRIES
  const maxFileBytes = options.maxFileBytes ?? DEFAULT_MAX_FILE_BYTES
  const maxTotalBytes = options.maxTotalBytes ?? DEFAULT_MAX_TOTAL_BYTES
    if (![maxDepth, maxFiles, maxEntries, maxFileBytes, maxTotalBytes].every(Number.isSafeInteger) ||
      maxDepth < 0 || maxFiles <= 0 || maxEntries <= 0 || maxFileBytes <= 0 || maxTotalBytes <= 0) {
    throw new TypeError('RAG limits must be positive safe integers')
  }

  const { files, truncated: filesTruncated } = collectFiles(root, maxDepth, maxFiles, maxEntries)
  const documents = []
  let bytesScanned = 0
  let skipped = 0
  let truncated = filesTruncated
  for (let index = 0; index < files.length; index += 1) {
    const remainingBytes = maxTotalBytes - bytesScanned
    if (remainingBytes <= 0) {
      truncated = true
      break
    }
    const file = readSafeText(files[index], workspaceRoot, maxFileBytes, remainingBytes)
    bytesScanned += file.bytesRead || 0
    if (!file || file.skipped || !file.content.trim()) {
      skipped += 1
      if (file.skipped === 'total_limit') truncated = true
      if (bytesScanned >= maxTotalBytes && index < files.length - 1) truncated = true
      continue
    }
    documents.push({
      id: Buffer.from(path.relative(workspaceRoot, files[index])).toString('base64'),
      file_path: path.relative(workspaceRoot, files[index]).split(path.sep).join('/'),
      content: file.content.slice(0, MAX_SNIPPET_CHARS)
    })
    if (bytesScanned >= maxTotalBytes && index < files.length - 1) {
      truncated = true
      break
    }
  }

  const embedText = options.embedText || Embeddings.embedText
  const indexedDocuments = []
  for (const document of documents) {
    indexedDocuments.push({
      ...document,
      embedding: JSON.stringify(await embedText(document.content)),
      created_at: Date.now()
    })
  }

  const dbPath = options.databasePath || DEFAULT_DATABASE_PATH
  fs.mkdirSync(path.dirname(dbPath), { recursive: true })
  const Database = databaseConstructor(options)
  const db = new Database(dbPath)
  try {
    db.prepare(`CREATE TABLE IF NOT EXISTS embeddings (
      id TEXT PRIMARY KEY,
      file_path TEXT NOT NULL,
      content TEXT NOT NULL,
      embedding TEXT NOT NULL,
      created_at INTEGER NOT NULL
    )`).run()
    db.prepare(`CREATE TABLE IF NOT EXISTS rag_index_metadata (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )`).run()
    const insert = db.prepare(`INSERT OR REPLACE INTO embeddings
      (id, file_path, content, embedding, created_at)
      VALUES (@id, @file_path, @content, @embedding, @created_at)`)
    const saveWorkspace = db.prepare(`INSERT OR REPLACE INTO rag_index_metadata
      (key, value) VALUES ('workspace_root', @workspace_root)`)
    const replaceIndex = db.transaction(() => {
      db.prepare('DELETE FROM embeddings').run()
      saveWorkspace.run({ workspace_root: workspaceRoot })
      for (const document of indexedDocuments) insert.run(document)
    })
    await replaceIndex()
  } finally {
    db.close()
  }
  return { indexed: documents.length, skipped, truncated, bytes_scanned: bytesScanned }
}

async function semanticSearch(query, options = {}) {
  if (typeof query !== 'string' || !query.trim() || query.length > MAX_QUERY_CHARS) {
    throw new RagInputError('INVALID_QUERY', 'Invalid search query')
  }
  const requestedResults = options.k ?? DEFAULT_MAX_RESULTS
  if (!Number.isSafeInteger(requestedResults) || requestedResults <= 0) {
    throw new RagInputError('INVALID_QUERY', 'Invalid result limit')
  }
  const maxResults = options.maxResults ?? DEFAULT_MAX_RESULTS
  const limit = Math.min(requestedResults, maxResults)
  const workspaceRoot = resolveWorkspaceRoot(options.workspaceRoot)
  const dbPath = options.databasePath || DEFAULT_DATABASE_PATH
  if (!fs.existsSync(dbPath)) return []

  const Database = databaseConstructor(options)
  const db = new Database(dbPath, { readonly: true, fileMustExist: true })
  try {
    let indexedWorkspace
    try {
      indexedWorkspace = db.prepare(
        "SELECT value FROM rag_index_metadata WHERE key = 'workspace_root'"
      ).get()
    } catch {
      return []
    }
    if (!indexedWorkspace || indexedWorkspace.value !== workspaceRoot) return []
    const rows = db.prepare('SELECT id, file_path, content, embedding FROM embeddings LIMIT ?')
      .all(DEFAULT_MAX_FILES)
    const embedText = options.embedText || Embeddings.embedText
    const queryVector = await embedText(query)
    const scored = rows.map((row) => {
      let vector
      try {
        vector = JSON.parse(row.embedding)
      } catch {
        vector = null
      }
      let score = -1
      if (Array.isArray(vector) && vector.length === queryVector.length) {
        let dot = 0
        let queryNorm = 0
        let vectorNorm = 0
        for (let index = 0; index < vector.length; index += 1) {
          dot += queryVector[index] * vector[index]
          queryNorm += queryVector[index] ** 2
          vectorNorm += vector[index] ** 2
        }
        if (queryNorm > 0 && vectorNorm > 0) score = dot / Math.sqrt(queryNorm * vectorNorm)
      }
      return { id: row.id, file_path: row.file_path, snippet: row.content, score }
    })
    scored.sort((left, right) => right.score - left.score)
    return scored.slice(0, limit)
  } finally {
    db.close()
  }
}

module.exports = {
  indexWorkspace,
  semanticSearch,
  RagInputError,
  resolveWorkspaceRoot,
  resolveRequestedRoot,
  DEFAULT_MAX_DEPTH,
  DEFAULT_MAX_FILES,
  DEFAULT_MAX_ENTRIES,
  DEFAULT_MAX_FILE_BYTES,
  DEFAULT_MAX_TOTAL_BYTES,
  DEFAULT_MAX_RESULTS,
  MAX_QUERY_CHARS
}
