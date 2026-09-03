const { spawn } = require('child_process')
const path = require('path')

const MODEL_PATH = path.resolve(__dirname, '..', '..', 'models', 'llama-3-8b.gguf')
const LLAMA_BIN = path.resolve(__dirname, 'bin', 'llama') // user should provide binary

async function query({message}){
  // Very small wrapper that calls llama.cpp CLI-style binary if available.
  // For production use embed a proper protocol or native ffi.
  return new Promise((resolve, reject)=>{
    try{
      const args = [
        '-m', MODEL_PATH,
        '-p', message,
        '--temp', '0.7',
        '--n', '128'
      ]
      const proc = spawn(LLAMA_BIN, args)
      let out = ''
      proc.stdout.on('data', (d)=> out += d.toString())
      proc.stderr.on('data', (d)=> console.error('llama err', d.toString()))
      proc.on('close', ()=>{
        resolve(out)
      })
    }catch(e){
      reject(e)
    }
  })
}

module.exports = { query }
