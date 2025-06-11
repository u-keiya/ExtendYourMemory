'use client'

import { useState, useEffect } from 'react'
import { Search, Loader2, FileText, Clock, Database, Shield, CheckCircle, AlertCircle } from 'lucide-react'
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

  // 初期ロード時にツール状態を取得
  useEffect(() => {
    fetchToolStatus()
  }, [])

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsSearching(true)
    setProgress(null)
    setResult(null)
    setError(null)

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
        } else if (data.event === 'search_complete') {
          setResult(data.data)
          setIsSearching(false)
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto">
        <header className="text-center py-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Extend Your Memory
          </h1>
          <p className="text-lg text-gray-600">
            あなたのデジタル記憶からAIが知識を検索・統合します
          </p>
        </header>

        {/* 認証状態表示 */}
        {toolStatus && (
          <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
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
                    <div className="font-medium">Google Drive</div>
                    <div className="text-sm text-gray-600">
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
                    <div className="font-medium">Chrome History</div>
                    <div className="text-sm text-gray-600">
                      {toolStatus.chrome_history.cache_valid 
                        ? `${toolStatus.chrome_history.cached_items}件のデータ` 
                        : '拡張機能が必要'}
                    </div>
                  </div>
                </div>
                {toolStatus.chrome_history.cache_valid ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                )}
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
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
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
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                生成されたレポート
              </h2>
              <div className="prose max-w-none">
                <ReactMarkdown>{result.report}</ReactMarkdown>
              </div>
            </div>

            {/* 検索統計 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-white rounded-lg shadow p-4 text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {result.total_documents}
                </div>
                <div className="text-sm text-gray-600">総ドキュメント数</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 text-center">
                <div className="text-2xl font-bold text-green-600">
                  {result.relevant_documents}
                </div>
                <div className="text-sm text-gray-600">関連ドキュメント数</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {result.keywords_used.length}
                </div>
                <div className="text-sm text-gray-600">使用キーワード数</div>
              </div>
              <div className="bg-white rounded-lg shadow p-4 text-center">
                <div className="text-2xl font-bold text-orange-600">
                  {result.rag_queries.length}
                </div>
                <div className="text-sm text-gray-600">RAGクエリ数</div>
              </div>
            </div>

            {/* 詳細情報 */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  使用されたキーワード
                </h3>
                <div className="flex flex-wrap gap-2">
                  {result.keywords_used.map((keyword, index) => (
                    <span
                      key={index}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>

              <div className="bg-white rounded-lg shadow-lg p-6">
                <h3 className="text-lg font-bold text-gray-900 mb-3">
                  RAG検索クエリ
                </h3>
                <ul className="space-y-2">
                  {result.rag_queries.map((query, index) => (
                    <li key={index} className="text-sm text-gray-700">
                      • {query}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}