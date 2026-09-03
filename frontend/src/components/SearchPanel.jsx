import React, {useState} from 'react'
import axios from 'axios'

export default function SearchPanel(){
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [indexing, setIndexing] = useState(false)

  async function handleIndex(){
    setIndexing(true)
    try{
      await axios.post('http://localhost:5174/api/rag/index')
      alert('Indexing started (completed synchronously in this prototype)')
    }catch(e){
      alert('Index failed: '+(e?.response?.data?.error||e.message))
    }finally{ setIndexing(false) }
  }

  async function handleSearch(){
    try{
      const r = await axios.post('http://localhost:5174/api/rag/search', {query, k:10})
      setResults(r.data.results || [])
    }catch(e){
      alert('Search failed: '+(e?.response?.data?.error||e.message))
    }
  }

  return (
    <div className="mt-6">
      <div className="text-sm text-gray-400 mb-2">Busca Semântica (RAG)</div>
      <div className="flex space-x-2">
        <input className="flex-1 bg-gray-800 px-2 py-2 rounded text-sm" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Digite sua busca..." />
        <button className="bg-blue-600 px-3 rounded" onClick={handleSearch}>Buscar</button>
      </div>
      <div className="mt-2 flex space-x-2">
        <button className="bg-green-600 px-3 rounded text-sm" onClick={handleIndex} disabled={indexing}>{indexing? 'Indexando...':'Indexar workspace'}</button>
      </div>
      <div className="mt-3 text-xs text-gray-400">Resultados:</div>
      <ul className="mt-2 space-y-2 text-sm">
        {results.map((r,idx)=>(
          <li key={r.id} className="p-2 bg-gray-800 rounded">
            <div className="text-xs text-gray-300">{r.file_path} — score: {typeof r.score==='number'?r.score.toFixed(4):r.score}</div>
            <pre className="text-xs mt-1 text-gray-200 max-h-24 overflow-auto">{r.snippet}</pre>
          </li>
        ))}
      </ul>
    </div>
  )
}
