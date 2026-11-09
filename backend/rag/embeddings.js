const crypto = require('crypto')

// Minimal local embedding fallback implementation.
// This is deterministic and lightweight and intended as a placeholder
// Replace with a proper call to Nomic Embeddings or other local model.

function textToVector(text, dim = 256){
  // Simple hashing-based projection: split text into tokens and accumulate hashed values
  const vec = new Array(dim).fill(0)
  const tokens = text.split(/\s+/).slice(0, 512)
  for(let i=0;i<tokens.length;i++){
    const t = tokens[i]
    const h = crypto.createHash('md5').update(t).digest()
    for(let j=0;j<dim;j++){
      vec[j] += h[j % h.length]
    }
  }
  // normalize
  const norm = Math.sqrt(vec.reduce((s,v)=>s+v*v,0)) || 1
  for(let i=0;i<dim;i++) vec[i] = vec[i]/norm
  return vec
}

async function embedText(text){
  // If you have Nomic embeddings CLI or library, replace this implementation
  // Example placeholder returns a 256-d vector
  return textToVector(text, 256)
}

module.exports = { embedText }
