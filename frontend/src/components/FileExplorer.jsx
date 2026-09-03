import React from 'react'

export default function FileExplorer(){
  return (
    <div>
      <div className="text-sm text-gray-400 mb-2">Explorer</div>
      <ul className="text-sm space-y-1">
        <li className="px-2 py-1 rounded hover:bg-gray-800 cursor-pointer">/workspace/project/main.py</li>
        <li className="px-2 py-1 rounded hover:bg-gray-800 cursor-pointer">/workspace/project/requirements.txt</li>
      </ul>
    </div>
  )
}
