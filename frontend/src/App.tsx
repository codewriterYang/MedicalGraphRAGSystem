import { useState, useRef, useCallback, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import UnifiedChatPanel from '@/components/UnifiedChatPanel'
import DebugPanel from '@/components/DebugPanel'
import GraphPanel from '@/components/GraphPanel'
import GraphRAGDebugPanel from '@/components/GraphRAGDebugPanel'
import type { DebugInfo, GraphData, GraphRAGDebugInfo, UnifiedMessage } from '@/types'
import { PanelRightClose, PanelRightOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'

const MIN_PANEL_WIDTH = 280
const DEFAULT_PANEL_WIDTH = 400
const MAX_PANEL_WIDTH = 800

function App() {
  const [debug, setDebug] = useState<DebugInfo | GraphRAGDebugInfo | null>(null)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [responseMode, setResponseMode] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [panelWidth, setPanelWidth] = useState(DEFAULT_PANEL_WIDTH)
  const [isResizing, setIsResizing] = useState(false)
  const startXRef = useRef(0)
  const startWidthRef = useRef(DEFAULT_PANEL_WIDTH)

  const handleResponse = (msg: UnifiedMessage) => {
    if (msg.debug !== undefined) setDebug(msg.debug)
    if (msg.graph_data !== undefined) setGraphData(msg.graph_data)
    if (msg.mode) setResponseMode(msg.mode)
  }

  const isGraphRAGMode = responseMode === 'graphrag'

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    setIsResizing(true)
    startXRef.current = e.clientX
    startWidthRef.current = panelWidth
    e.preventDefault()
  }, [panelWidth])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      const delta = startXRef.current - e.clientX
      const newWidth = Math.max(MIN_PANEL_WIDTH, Math.min(MAX_PANEL_WIDTH, startWidthRef.current + delta))
      setPanelWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  return (
    <div className="h-screen flex flex-col select-none">
      <header className="h-12 border-b flex items-center px-4 shrink-0 bg-white">
        <span className="font-semibold">🏥 医药知识图谱智能问答系统</span>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        <div className="flex-1 min-w-0">
          <UnifiedChatPanel onResponse={handleResponse} />
        </div>

        {panelOpen && (
          <>
            <div
              className={`w-1 shrink-0 cursor-col-resize bg-transparent hover:bg-primary/20 transition-colors ${isResizing ? 'bg-primary/30' : ''}`}
              onMouseDown={handleMouseDown}
              title="拖动调整宽度"
            />
            <div
              className="shrink-0 flex flex-col bg-white border-l"
              style={{ width: panelWidth }}
            >
              <div className="h-10 border-b flex items-center justify-end px-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 w-7 p-0"
                  onClick={() => setPanelOpen(false)}
                  title="收起面板"
                >
                  <PanelRightClose className="h-4 w-4" />
                </Button>
              </div>
              <Tabs defaultValue="debug" className="flex flex-col flex-1 min-h-0">
                <TabsList className="mx-4 mt-2 shrink-0">
                  <TabsTrigger value="debug">调试信息</TabsTrigger>
                  <TabsTrigger value="graph">知识图谱</TabsTrigger>
                </TabsList>
                <TabsContent value="debug" className="flex-1 overflow-hidden m-0">
                  {isGraphRAGMode ? (
                    <GraphRAGDebugPanel debug={debug as GraphRAGDebugInfo | null} />
                  ) : (
                    <DebugPanel debug={debug as DebugInfo | null} />
                  )}
                </TabsContent>
                <TabsContent value="graph" className="flex-1 overflow-hidden m-0" keepMounted>
                  <GraphPanel graphData={graphData} />
                </TabsContent>
              </Tabs>
            </div>
          </>
        )}

        {!panelOpen && (
          <div className="absolute right-0 top-1/2 -translate-y-1/2 z-10">
            <Button
              variant="outline"
              size="icon"
              className="h-10 w-6 rounded-l-md rounded-r-none border-r-0"
              onClick={() => setPanelOpen(true)}
              title="展开面板"
            >
              <PanelRightOpen className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
