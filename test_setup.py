#!/usr/bin/env python3
"""
Extend Your Memory - End-to-End Test Setup
"""

import asyncio
import json
import os
import requests
import websockets
from datetime import datetime

async def test_mcp_server():
    """MCPサーバーのテスト"""
    print("🔧 Testing MCP Server...")
    
    try:
        # MCPサーバーが起動しているかチェック
        response = requests.get("http://localhost:8501/health", timeout=5)
        if response.status_code == 200:
            print("✅ MCP Server is running")
        else:
            print("❌ MCP Server is not responding properly")
            return False
    except requests.exceptions.RequestException:
        print("❌ MCP Server is not accessible")
        return False
    
    # ツール状態をチェック
    try:
        response = requests.post(
            "http://localhost:8501/tools/check_tools_status",
            json={},
            timeout=10
        )
        if response.status_code == 200:
            status = response.json()
            print("📊 MCP Tools Status:")
            print(f"   Google Drive: {status.get('google_drive', {})}")
            print(f"   Chrome History: {status.get('chrome_history', {})}")
            print(f"   Mistral OCR: {status.get('mistral_ocr', {})}")
        else:
            print("⚠️  Could not retrieve MCP tools status")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Error checking MCP tools: {e}")
    
    return True

async def test_backend_api():
    """バックエンドAPIのテスト"""
    print("\n🔧 Testing Backend API...")
    
    try:
        # ヘルスチェック
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API is running")
        else:
            print("❌ Backend API is not responding properly")
            return False
    except requests.exceptions.RequestException:
        print("❌ Backend API is not accessible")
        return False
    
    # RESTful検索のテスト
    try:
        print("🔍 Testing search endpoint...")
        response = requests.post(
            "http://localhost:8000/search",
            json={"query": "LLMの最新技術動向について"},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ Search endpoint working")
            print(f"   Keywords used: {result.get('keywords_used', [])}")
            print(f"   Total documents: {result.get('total_documents', 0)}")
            print(f"   Relevant documents: {result.get('relevant_documents', 0)}")
            print(f"   Report length: {len(result.get('report', ''))}")
        else:
            print(f"❌ Search endpoint failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Search endpoint error: {e}")
        return False
    
    return True

async def test_websocket_search():
    """WebSocket検索のテスト"""
    print("\n🔧 Testing WebSocket Search...")
    
    try:
        uri = "ws://localhost:8000/ws/search"
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket connection established")
            
            # 検索リクエストを送信
            search_request = {
                "query": "AI技術の最新動向"
            }
            await websocket.send(json.dumps(search_request))
            print("📤 Search request sent")
            
            # 進捗メッセージを受信
            progress_count = 0
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=60)
                    data = json.loads(message)
                    
                    if data["event"] == "search_progress":
                        progress_count += 1
                        progress = data["data"]
                        print(f"   Step {progress['step']}: {progress['message']}")
                    
                    elif data["event"] == "search_complete":
                        result = data["data"]
                        print("✅ WebSocket search completed")
                        print(f"   Keywords: {result.get('keywords_used', [])}")
                        print(f"   Documents: {result.get('total_documents', 0)}")
                        print(f"   Progress steps: {progress_count}")
                        break
                    
                    elif data["event"] == "error":
                        print(f"❌ WebSocket search error: {data.get('message', 'Unknown error')}")
                        return False
                        
                except asyncio.TimeoutError:
                    print("❌ WebSocket search timeout")
                    return False
                    
    except Exception as e:
        print(f"❌ WebSocket connection error: {e}")
        return False
    
    return True

async def test_frontend():
    """フロントエンドのテスト"""
    print("\n🔧 Testing Frontend...")
    
    try:
        response = requests.get("http://localhost:3000", timeout=10)
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            if "Extend Your Memory" in response.text:
                print("✅ Frontend content looks correct")
            else:
                print("⚠️  Frontend content may be incorrect")
        else:
            print(f"❌ Frontend returned status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Frontend is not accessible: {e}")
        return False
    
    return True

async def check_environment():
    """環境変数とセットアップのチェック"""
    print("🔧 Checking Environment Setup...")
    
    required_vars = [
        "GOOGLE_API_KEY",
        "MCP_SERVER_URL"
    ]
    
    optional_vars = [
        "GOOGLE_DRIVE_API_KEY", 
        "CHROME_API_KEY",
        "MISTRAL_OCR_API_KEY"
    ]
    
    print("📋 Required Environment Variables:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * min(len(value), 10)}... (configured)")
        else:
            print(f"   ❌ {var}: Not configured")
    
    print("📋 Optional Environment Variables:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"   ✅ {var}: {'*' * min(len(value), 10)}... (configured)")
        else:
            print(f"   ⚠️  {var}: Not configured (will use mock)")

async def run_full_test():
    """完全なエンドツーエンドテスト"""
    print("🚀 Starting End-to-End Test for Extend Your Memory")
    print("=" * 60)
    
    # 環境チェック
    await check_environment()
    
    # 各コンポーネントのテスト
    tests = [
        ("MCP Server", test_mcp_server),
        ("Backend API", test_backend_api),
        ("WebSocket Search", test_websocket_search),
        ("Frontend", test_frontend)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results[test_name] = False
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready to use.")
        print("\n🌐 Access the application at: http://localhost:3000")
    else:
        print("⚠️  Some tests failed. Please check the configuration and try again.")
        print("\n💡 Common issues:")
        print("   - Make sure all services are running (docker-compose up)")
        print("   - Check environment variables (.env file)")
        print("   - Verify API keys are correctly configured")

if __name__ == "__main__":
    asyncio.run(run_full_test())