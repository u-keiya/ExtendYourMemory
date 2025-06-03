'use client'

import { useState } from 'react'
import { Search, Loader2, FileText, Clock, Database } from 'lucide-react'
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

export default function Home() {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [progress, setProgress] = useState<SearchProgress | null>(null)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)

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

        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex gap-4 mb-4">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
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