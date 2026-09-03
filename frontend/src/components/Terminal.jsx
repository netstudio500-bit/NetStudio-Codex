import React, {useEffect, useRef} from 'react'
import { Terminal as XTerminal } from 'xterm'
import 'xterm/css/xterm.css'

export default function Terminal(){
  const ref = useRef(null)

  useEffect(()=>{
    const term = new XTerminal({cols:80, rows:10})
    term.open(ref.current)
    term.writeln('Welcome to Freebuff Local terminal')
    return ()=> term.dispose()
  },[])

  return <div ref={ref} className="h-full bg-black"></div>
}
