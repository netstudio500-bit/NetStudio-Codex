import React from 'react'

export default function ChatSidebar(){
  return (
    <div className="mt-6">
      <div className="text-sm text-gray-400 mb-2">IA Chat</div>
      <div className="space-y-2">
        <button className="w-full bg-gray-800 hover:bg-gray-700 text-sm py-2 rounded">Nova conversa</button>
        <div className="text-xs text-gray-500 mt-3">Conversas recentes</div>
      </div>
    </div>
  )
}
