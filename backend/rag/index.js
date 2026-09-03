const fs = require('fs')
const path = require('path')
const Embeddings = require('./embeddings')
const Database = require('better-sqlite3')

async function indexWorkspace(rootPath){
  const dbPath = path.join(__dirname, '..', 'data', 'rag.db')
  const dir = path.dirname(dbPath)
  if(!fs.existsSync(dir)) fs.mkdirSync(dir, {recursive:true})
  const db = new Database(dbPath)

  db.prepare(`CREATE TABLE IF NOT EXISTS embeddings (
    id TEXT PRIMARY KEY,
    file_path TEXT,
    content TEXT,
    embedding TEXT,
    created_at INTEGER
  )`).run()

  function walkDir(dirPath, fileList = []){
    const entries = fs.readdirSync(dirPath, {withFileTypes:true})
    for(const e of entries){
      const full = path.join(dirPath, e.name)
      if(e.isDirectory()) walkDir(full, fileList)
      else if(e.isFile()) fileList.push(full)
    }
    return fileList
  }

  const files = walkDir(rootPath)
  const insertStmt = db.prepare('INSERT OR REPLACE INTO embeddings (id, file_path, content, embedding, created_at) VALUES (@id,@file_path,@content,@embedding,@created_at)')

  for(const file of files){
    try{
      const ext = path.extname(file).toLowerCase()
      // Skip binary-ish files
      if(['.png','.jpg','.jpeg','.gif','.exe','.dll','.so','.bin','.gguf'].includes(ext)) continue
      const content = fs.readFileSync(file, 'utf8')
      if(!content || content.trim().length===0) continue
      const vector = await Embeddings.embedText(content)
      const id = Buffer.from(file).toString('base64')
      insertStmt.run({
        id,
        file_path: path.relative(rootPath, file),
        content: content.substring(0, 4000), // limit size
        embedding: JSON.stringify(vector),
        created_at: Date.now()
      })
    }catch(e){
      // skip files that can't be read
      console.warn('index error', file, e.message)
    }
  }

  db.close()
  return {indexed: files.length}
}

async function semanticSearch(query, opts = {}){
  const k = opts.k || 5
  const dbPath = path.join(__dirname, '..', 'data', 'rag.db')
  if(!fs.existsSync(dbPath)) return []
  const db = new Database(dbPath)

  const rows = db.prepare('SELECT id, file_path, content, embedding FROM embeddings').all()
  const qvec = await Embeddings.embedText(query)

  function cosine(a,b){
    let dot = 0, na = 0, nb = 0
    for(let i=0;i<a.length;i++){
      dot += a[i]*b[i]
      na += a[i]*a[i]
      nb += b[i]*b[i]
    }
    if(na===0||nb===0) return 0
    return dot/Math.sqrt(na*nb)
  }

  const scored = rows.map(r=>{
    let vec
    try{ vec = JSON.parse(r.embedding) }catch(e){ vec = null }
    const score = vec ? cosine(qvec, vec) : -1
    return {id:r.id, file_path: r.file_path, snippet: r.content, score}
  })

  scored.sort((a,b)=>b.score - a.score)
  db.close()
  return scored.slice(0,k)
}

module.exports = { indexWorkspace, semanticSearch }
