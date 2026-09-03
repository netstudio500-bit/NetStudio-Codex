const express = require('express')
const http = require('http')
const { Server } = require('socket.io')
const path = require('path')
const cors = require('cors')
const bodyParser = require('body-parser')

const initDb = require('./database/init')
const ll = require('./llama/llama')

const app = express()
const server = http.createServer(app)
const io = new Server(server, { cors: { origin: '*' } })

app.use(cors())
app.use(bodyParser.json())

const db = initDb(path.join(__dirname, 'data', 'freebuff.db'))

app.get('/api/health', (req,res)=> res.json({ok:true}))

// Files API (simple)
app.get('/api/files', (req,res)=>{
  // placeholder: list workspace files
  res.json({files:["/workspace/project/main.py","/workspace/project/README.md"]})
})

// Chat API for simple request-response (calls local llama bridge)
app.post('/api/chat', async (req,res)=>{
  const {message, conversationId} = req.body
  try{
    const reply = await ll.query({message})
    // save in DB (placeholder)
    res.json({reply})
  }catch(err){
    console.error(err)
    res.status(500).json({error:err.message})
  }
})

io.on('connection', (socket)=>{
  console.log('ws connected', socket.id)
  socket.on('chat:message', async (payload)=>{
    try{
      const reply = await ll.query({message: payload.message})
      socket.emit('chat:reply', {reply})
    }catch(e){
      socket.emit('chat:error', {error: e.message})
    }
  })
})

const PORT = process.env.PORT || 5174
server.listen(PORT, ()=> console.log('Backend running on', PORT))
