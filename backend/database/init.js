const Database = require('better-sqlite3')
const fs = require('fs')
const path = require('path')

module.exports = function(dbPath){
  const dir = path.dirname(dbPath)
  if(!fs.existsSync(dir)) fs.mkdirSync(dir, {recursive:true})
  const db = new Database(dbPath)

  // Create tables
  db.prepare(`CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at INTEGER
  )`).run()

  db.prepare(`CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,
    content TEXT,
    created_at INTEGER
  )`).run()

  db.prepare(`CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
  )`).run()

  return db
}
