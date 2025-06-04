# Extend Your Memory

AI-powered search and report generation from your digital memory (Google Drive, Browser History, Web Pages).

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Copy environment file and configure your API keys
cp .env.example .env
# Edit .env file with your actual API keys
```

### 2. Easy Development Startup

```bash
# Use the convenient startup script
./run_dev.sh
```

### 3. Manual Development Mode

```bash
# Start all services with Docker Compose
docker compose up --build

# Or start individual services:

# MCP Server
cd mcp-server && python server.py

# Backend API
cd backend && uvicorn main:app --reload

# Frontend
cd frontend && npm run dev
```

### 4. Testing

```bash
# Run end-to-end tests
python test_setup.py
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **MCP Server**: http://localhost:8501

## 🏗️ Architecture

- **Frontend**: Next.js 14 with TypeScript and Tailwind CSS
- **Backend**: FastAPI with WebSocket support
- **MCP Server**: Custom MCP tools for external data integration
- **Vector Database**: FAISS for local vector storage
- **LLM Integration**: Google Gemini 2.5 Flash

## 📋 Required API Keys

1. **Google API Key**: For embeddings and LLM access
2. **Google Drive API Key**: For Google Drive file access
3. **Mistral OCR API Key**: For PDF OCR processing

## 🛠️ Development Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# MCP Server
cd mcp-server
pip install -r requirements.txt
python server.py
```

## 📁 Project Structure

```
ExtendYourMemory/
├── mcp-server/          # MCP server for external data tools
├── backend/             # FastAPI backend with RAG pipeline
├── frontend/            # Next.js frontend application
├── docker-compose.yml   # Docker orchestration
└── README.md           # This file
```

## 🔒 Security Note

- API keys are stored in environment variables
- Chrome history access requires explicit user permission
- Vector store data can be periodically cleared

## 📖 Documentation

For detailed technical specifications, see `description.md`.
For development guidance, see `CLAUDE.md`.