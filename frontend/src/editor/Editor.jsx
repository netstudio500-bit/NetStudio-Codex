import React, {useRef, useState} from 'react'
import Editor from '@monaco-editor/react'

export default function CodeEditor(){
  const [value, setValue] = useState('// Selecione um arquivo para editar')
  const monacoRef = useRef(null)

  function handleEditorDidMount(editor, monaco){
    monacoRef.current = editor
  }

  return (
    <div className="h-full">
      <Editor
        height="100%"
        defaultLanguage="javascript"
        defaultValue={value}
        onMount={handleEditorDidMount}
        theme="vs-dark"
      />
    </div>
  )
}
