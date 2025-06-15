'use client'

import { useState, useEffect } from 'react'
import { Search, Loader2, FileText, Clock, Database, Shield, CheckCircle, AlertCircle, ChevronLeft, ChevronRight, MessageSquare, Link2, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface SearchProgress {
  step: number
  stage: string
  message: string
  details?: any
}

interface SearchResult {
  report: string
  sources: any[]
  keywords_used: string[]
  rag_queries: string[]
  total_documents: number
  relevant_documents: number
  rag_results?: any[]
}

interface ChatHistory {
  id: string
  query: string
  timestamp: Date
  result?: SearchResult
}

interface ToolStatus {
  google_drive: {
    service_initialized: boolean
    credentials_available: boolean
    authentication_method: string
    oauth_flow_configured: boolean
    needs_authentication: boolean
    langchain_available: boolean
  }
  chrome_history: {
    tool_type: string
    cache_valid: boolean
    cached_items: number
    extension_communication: string
  }
  mistral_ocr: {
    api_key_configured: boolean
    client_initialized: boolean
    status: string
  }
}

export default function Home() {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [progress, setProgress] = useState<SearchProgress | null>(null)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [toolStatus, setToolStatus] = useState<ToolStatus | null>(null)
  const [isAuthenticating, setIsAuthenticating] = useState(false)
  const [chatHistory, setChatHistory] = useState<ChatHistory[]>(() => {
    // ローカルストレージから会話履歴を復元
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('extendYourMemory_chatHistory')
        if (saved) {
          const parsed = JSON.parse(saved)
          return parsed.map((chat: any) => ({
            ...chat,
            timestamp: new Date(chat.timestamp)
          }))
        }
      } catch (error) {
        console.error('Failed to load chat history:', error)
      }
    }
    return []
  })
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [isLeftSidebarOpen, setIsLeftSidebarOpen] = useState(true)
  const [isRightSidebarOpen, setIsRightSidebarOpen] = useState(true)
  const [ragResults, setRagResults] = useState<any[]>([])

  const mcpServerUrl = 'http://localhost:8501'

  // ツール状態を取得
  const fetchToolStatus = async () => {
    try {
      const response = await fetch(`${mcpServerUrl}/tools/check_tools_status`)
      if (response.ok) {
        const status = await response.json()
        setToolStatus(status)
      }
    } catch (error) {
      console.error('Failed to fetch tool status:', error)
    }
  }

  // Google Drive認証を開始
  const handleGoogleAuth = async () => {
    try {
      setIsAuthenticating(true)
      const response = await fetch(`${mcpServerUrl}/auth/google/login`)
      
      if (response.ok) {
        const data = await response.json()
        // 新しいウィンドウで認証URLを開く
        const authWindow = window.open(
          data.auth_url,
          'google-auth',
          'width=500,height=600,scrollbars=yes,resizable=yes'
        )

        // 認証完了をポーリングで確認
        const checkAuth = setInterval(async () => {
          try {
            const statusResponse = await fetch(`${mcpServerUrl}/tools/check_tools_status`)
            if (statusResponse.ok) {
              const status = await statusResponse.json()
              if (status.google_drive.credentials_available) {
                clearInterval(checkAuth)
                setToolStatus(status)
                setIsAuthenticating(false)
                if (authWindow) authWindow.close()
              }
            }
          } catch (error) {
            console.error('Auth check failed:', error)
          }
        }, 2000)

        // 30秒でタイムアウト
        setTimeout(() => {
          clearInterval(checkAuth)
          setIsAuthenticating(false)
          if (authWindow) authWindow.close()
        }, 30000)

      } else {
        throw new Error('Failed to get auth URL')
      }
    } catch (error) {
      console.error('Authentication failed:', error)
      setIsAuthenticating(false)
    }
  }

  // Chrome Extension状態チェック
  const checkExtensionStatus = async () => {
    try {
      const bridge: any = (window as any).ExtendYourMemoryBridge
      if (bridge) {
        const isAvailable = await bridge.testExtensionConnection().catch(() => false)
        console.log('Extension status check:', isAvailable)
        return isAvailable
      }
      return false
    } catch (e) {
      console.debug('Extension status check failed:', e)
      return false
    }
  }

  // 初期ロード時にツール状態を取得
  useEffect(() => {
    fetchToolStatus()
    
    // Chrome Extension状態を定期的にチェック
    const checkExtension = async () => {
      const available = await checkExtensionStatus()
      if (available) {
        // 拡張機能が利用可能なら、ツール状態を再取得
        fetchToolStatus()
      }
    }
    
    // 初回チェック
    setTimeout(checkExtension, 1000)
    
    // 定期チェック（30秒ごと）
    const interval = setInterval(checkExtension, 30000)
    
    return () => clearInterval(interval)
  }, [])

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsSearching(true)
    setProgress(null)
    setResult(null)
    setError(null)

    // Ask Chrome extension to send latest history to the server if available
    try {
      const bridge: any = (window as any).ExtendYourMemoryBridge
      if (bridge) {
        // Test extension connection first
        const isAvailable = await bridge.testExtensionConnection().catch(() => false)
        console.log('Extension connection test:', isAvailable)
        
        if (isAvailable) {
          console.log('Refreshing Chrome history...')
          await bridge.refreshHistory().catch((error: any) => {
            console.warn('Extension refresh failed:', error)
          })
        } else {
          console.warn('Chrome extension not responding')
        }
      } else {
        console.warn('Chrome extension bridge not found')
      }
    } catch (e) {
      console.debug('Extension communication error:', e)
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const wsUrl = apiUrl.replace('http', 'ws') + '/ws/search'
      
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        ws.send(JSON.stringify({ query }))
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        
        if (data.event === 'search_progress') {
          setProgress(data.data)
          // RAG検索の結果を保存
          if (data.data.stage === 'rag_search_complete' && data.data.details) {
            setRagResults(data.data.details.results || [])
          }
        } else if (data.event === 'search_complete') {
          const result = data.data
          setResult(result)
          setIsSearching(false)
          
          // チャット履歴に追加
          const newChat: ChatHistory = {
            id: Date.now().toString(),
            query,
            timestamp: new Date(),
            result
          }
          const updatedHistory = [newChat, ...chatHistory]
          setChatHistory(updatedHistory)
          setSelectedChatId(newChat.id)
          
          // ローカルストレージに保存（最新50件まで）
          try {
            const historyToSave = updatedHistory.slice(0, 50)
            localStorage.setItem('extendYourMemory_chatHistory', JSON.stringify(historyToSave))
          } catch (error) {
            console.error('Failed to save chat history:', error)
          }
          
          // 検索完了後にツール状態を更新
          fetchToolStatus()
        } else if (data.event === 'error') {
          setError(data.message)
          setIsSearching(false)
        }
      }
      
      ws.onerror = () => {
        setError('WebSocket接続エラーが発生しました')
        setIsSearching(false)
      }
      
    } catch (err) {
      setError('検索中にエラーが発生しました')
      setIsSearching(false)
    }
  }

  const getProgressIcon = (stage: string) => {
    switch (stage) {
      case 'keyword_generation':
        return <Search className="h-4 w-4" />
      case 'mcp_search':
        return <Database className="h-4 w-4" />
      case 'vectorization':
        return <FileText className="h-4 w-4" />
      case 'rag_search':
        return <Search className="h-4 w-4" />
      case 'report_generation':
        return <FileText className="h-4 w-4" />
      default:
        return <Clock className="h-4 w-4" />
    }
  }

  const selectChat = (chatId: string) => {
    const chat = chatHistory.find(c => c.id === chatId)
    if (chat) {
      setSelectedChatId(chatId)
      setQuery(chat.query)
      setResult(chat.result || null)
      setProgress(null)
      setError(null)
    }
  }

  const clearChatHistory = () => {
    if (confirm('会話履歴をすべて削除しますか？')) {
      setChatHistory([])
      setSelectedChatId(null)
      localStorage.removeItem('extendYourMemory_chatHistory')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex">
      {/* 左サイドバー - 会話履歴 */}
      <div className={`transition-all duration-300 ${isLeftSidebarOpen ? 'w-80' : 'w-12'} bg-white shadow-lg flex flex-col`}>
        <div className="p-4 border-b">
          {isLeftSidebarOpen && (
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-semibold text-black flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                会話履歴
              </h2>
              {chatHistory.length > 0 && (
                <button
                  onClick={clearChatHistory}
                  className="p-1 hover:bg-red-100 rounded text-red-600"
                  title="履歴を削除"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              )}
            </div>
          )}
          <button
            onClick={() => setIsLeftSidebarOpen(!isLeftSidebarOpen)}
            className="p-1 hover:bg-gray-100 rounded"
          >
            {isLeftSidebarOpen ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </button>
        </div>
        
        {isLeftSidebarOpen && (
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {chatHistory.map((chat) => (
              <div
                key={chat.id}
                onClick={() => selectChat(chat.id)}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedChatId === chat.id
                    ? 'bg-blue-100 border-blue-300'
                    : 'bg-gray-50 hover:bg-gray-100 border-gray-200'
                } border`}
              >
                <div className="font-medium text-sm text-black truncate mb-1">
                  {chat.query}
                </div>
                <div className="text-xs text-gray-500">
                  {chat.timestamp.toLocaleString('ja-JP')}
                </div>
              </div>
            ))}
            {chatHistory.length === 0 && (
              <div className="text-center text-gray-500 text-sm py-8">
                まだ会話履歴がありません
              </div>
            )}
          </div>
        )}
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="max-w-4xl mx-auto">
        <header className="text-center py-8">
          <h1 className="text-4xl font-bold text-black mb-2">
            Extend Your Memory
          </h1>
          <p className="text-lg text-black">
            あなたのデジタル記憶からAIが知識を検索・統合します
          </p>
        </header>

        {/* 認証状態表示 */}
        {toolStatus && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-black mb-4 flex items-center gap-2">
              <Shield className="h-5 w-5" />
              データソース接続状況
            </h2>
            <div className="grid md:grid-cols-2 gap-4">
              {/* Google Drive */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`h-3 w-3 rounded-full ${
                    toolStatus.google_drive.credentials_available 
                      ? 'bg-green-500' 
                      : 'bg-red-500'
                  }`} />
                  <div>
                    <div className="font-medium text-black">Google Drive</div>
                    <div className="text-sm text-black">
                      {toolStatus.google_drive.credentials_available 
                        ? '接続済み' 
                        : '未接続'}
                    </div>
                  </div>
                </div>
                {toolStatus.google_drive.needs_authentication && (
                  <button
                    onClick={handleGoogleAuth}
                    disabled={isAuthenticating}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    {isAuthenticating ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        認証中...
                      </>
                    ) : (
                      <>
                        <Shield className="h-4 w-4" />
                        接続
                      </>
                    )}
                  </button>
                )}
                {toolStatus.google_drive.credentials_available && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
              </div>

              {/* Chrome History */}
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className={`h-3 w-3 rounded-full ${
                    toolStatus.chrome_history.cache_valid 
                      ? 'bg-green-500' 
                      : 'bg-yellow-500'
                  }`} />
                  <div>
                    <div className="font-medium text-black">Chrome History</div>
                    <div className="text-sm text-black">
                      {toolStatus.chrome_history.cache_valid 
                        ? `${toolStatus.chrome_history.cached_items}件のデータ` 
                        : '拡張機能が必要'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {!toolStatus.chrome_history.cache_valid && (
                    <button
                      onClick={async () => {
                        const available = await checkExtensionStatus()
                        if (available) {
                          await fetchToolStatus()
                        } else {
                          alert('Chrome拡張機能が検出されません。拡張機能をインストールしてページを再読み込みしてください。')
                        }
                      }}
                      className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                      テスト
                    </button>
                  )}
                  {toolStatus.chrome_history.cache_valid ? (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-yellow-500" />
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex gap-4 mb-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="何について調べたいですか？（例：LLMの最新技術動向について）"
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-black"
              disabled={isSearching}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching || !query.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSearching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              検索
            </button>
          </div>

          {/* 検索進捗表示 */}
          {progress && (
            <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
              <div className="flex items-center gap-3 mb-2">
                {getProgressIcon(progress.stage)}
                <span className="font-medium text-blue-900">
                  ステップ {progress.step}: {progress.message}
                </span>
              </div>
              {progress.details && (
                <div className="text-sm text-blue-700 ml-7">
                  {JSON.stringify(progress.details, null, 2)}
                </div>
              )}
            </div>
          )}

          {/* エラー表示 */}
          {error && (
            <div className="mb-4 p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* 検索結果表示 */}
        {result && (
          <div className="space-y-6">
            {/* レポート */}
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-2xl font-bold text-black mb-4">
                生成されたレポート
              </h2>
              <div className="prose prose-lg max-w-none text-black prose-headings:text-black prose-p:text-black prose-li:text-black prose-strong:text-black prose-a:text-blue-600 prose-a:underline hover:prose-a:text-blue-800">
                <ReactMarkdown 
                  className="text-black"
                  components={{
                    h1: ({node, ...props}) => <h1 className="text-2xl font-bold text-black mb-4" {...props} />,
                    h2: ({node, ...props}) => <h2 className="text-xl font-semibold text-black mb-3 mt-6" {...props} />,
                    h3: ({node, ...props}) => <h3 className="text-lg font-medium text-black mb-2 mt-4" {...props} />,
                    p: ({node, ...props}) => <p className="text-black mb-3 leading-relaxed" {...props} />,
                    ul: ({node, ...props}) => <ul className="list-disc pl-5 mb-3 text-black" {...props} />,
                    ol: ({node, ...props}) => <ol className="list-decimal pl-5 mb-3 text-black" {...props} />,
                    li: ({node, ...props}) => <li className="text-black mb-1" {...props} />,
                    a: ({node, ...props}) => <a className="text-blue-600 underline hover:text-blue-800" target="_blank" rel="noopener noreferrer" {...props} />,
                    strong: ({node, ...props}) => <strong className="font-bold text-black" {...props} />,
                    em: ({node, ...props}) => <em className="italic text-black" {...props} />,
                    blockquote: ({node, ...props}) => <blockquote className="border-l-4 border-gray-300 pl-4 italic text-black" {...props} />,
                    code: ({node, ...props}) => <code className="bg-gray-100 px-1 py-0.5 rounded text-black font-mono text-sm" {...props} />
                  }}
                >
                  {result.report}
                </ReactMarkdown>
              </div>
            </div>

          </div>
        )}
        </div>
      </div>

      {/* 右サイドバー - RAG検索結果 */}
      <div className={`transition-all duration-300 ${isRightSidebarOpen ? 'w-80' : 'w-12'} bg-white shadow-lg flex flex-col`}>
        <div className="p-4 border-b flex items-center justify-between">
          <button
            onClick={() => setIsRightSidebarOpen(!isRightSidebarOpen)}
            className="p-1 hover:bg-gray-100 rounded"
          >
            {isRightSidebarOpen ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
          </button>
          {isRightSidebarOpen && (
            <h2 className="font-semibold text-black flex items-center gap-2">
              <Link2 className="h-5 w-5" />
              検索結果詳細
            </h2>
          )}
        </div>
        
        {isRightSidebarOpen && (
          <div className="flex-1 overflow-y-auto p-4">
            {result && (
              <div className="space-y-4">
                {/* 検索統計 */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium text-black mb-3">検索統計</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-black">総ドキュメント:</span>
                      <span className="font-medium text-blue-600">{result.total_documents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-black">関連ドキュメント:</span>
                      <span className="font-medium text-green-600">{result.relevant_documents}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-black">キーワード数:</span>
                      <span className="font-medium text-purple-600">{result.keywords_used.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-black">RAGクエリ数:</span>
                      <span className="font-medium text-orange-600">{result.rag_queries.length}</span>
                    </div>
                  </div>
                </div>

                {/* 使用キーワード */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium text-black mb-3">使用キーワード</h3>
                  <div className="flex flex-wrap gap-2">
                    {result.keywords_used.map((keyword, index) => (
                      <span
                        key={index}
                        className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs"
                      >
                        {keyword}
                      </span>
                    ))}
                  </div>
                </div>

                {/* RAGクエリ */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h3 className="font-medium text-black mb-3">RAGクエリ</h3>
                  <div className="space-y-2">
                    {result.rag_queries.map((query, index) => (
                      <div key={index} className="text-xs text-black bg-white p-2 rounded border">
                        {query}
                      </div>
                    ))}
                  </div>
                </div>


                {/* RAG検索結果 */}
                {ragResults.length > 0 && (
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-medium text-black mb-3">RAG検索結果</h3>
                    <div className="space-y-2">
                      {ragResults.slice(0, 5).map((ragResult, index) => (
                        <div key={index} className="text-xs text-black bg-white p-2 rounded border">
                          <div className="font-medium mb-1">
                            スコア: {ragResult.score?.toFixed(3) || 'N/A'}
                          </div>
                          <div className="text-black mb-2">
                            {ragResult.content?.substring(0, 150) || ragResult.page_content?.substring(0, 150)}...
                          </div>
                          {ragResult.metadata?.source && (
                            <div className="text-xs mt-1">
                              {ragResult.metadata.source.startsWith('http') ? (
                                <a
                                  href={ragResult.metadata.source}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                                >
                                  <Link2 className="h-3 w-3" />
                                  {ragResult.metadata.source}
                                </a>
                              ) : (
                                <span className="text-gray-600">
                                  出典: {ragResult.metadata.source}
                                </span>
                              )}
                            </div>
                          )}
                          {ragResult.metadata?.url && (
                            <div className="text-xs mt-1">
                              <a
                                href={ragResult.metadata.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                              >
                                <Link2 className="h-3 w-3" />
                                元のページを開く
                              </a>
                            </div>
                          )}
                          {ragResult.metadata?.title && (
                            <div className="text-xs mt-1 font-medium text-gray-700">
                              {ragResult.metadata.title}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {!result && (
              <div className="text-center text-gray-500 text-sm py-8">
                検索を実行すると結果の詳細が表示されます
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}