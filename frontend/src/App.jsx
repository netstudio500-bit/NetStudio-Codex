import React from 'react'
import FileExplorer from './components/FileExplorer'
import Editor from './components/Editor'
import ChatSidebar from './components/ChatSidebar'
import Terminal from './components/Terminal'
import SearchPanel from './components/SearchPanel'

export default function App(){
  return (
    <div className="h-screen flex">
      <aside className="w-80 border-r border-gray-800 p-3 bg-gray-900">
        <div className="mb-4 text-lg font-semibold">Freebuff Local</div>
        <FileExplorer />
        <SearchPanel />
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
