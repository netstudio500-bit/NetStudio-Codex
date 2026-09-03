import React from 'react'
import FileExplorer from './components/FileExplorer'
import Editor from './components/Editor'
import ChatSidebar from './components/ChatSidebar'
import Terminal from './components/Terminal'

export default function App(){
  return (
    <div className="h-screen flex">
      <aside className="w-72 border-r border-gray-800 p-2 bg-gray-900">
        <div className="mb-4 text-lg font-semibold">Freebuff Local</div>
        <FileExplorer />
        <ChatSidebar />
      </aside>
      <main className="flex-1 flex flex-col">
        <div className="flex-1 relative">
          <Editor />
        </div>
        <div className="h-40 border-t border-gray-800">
          <Terminal />
        </div>
      </main>
    </div>
  )
}
