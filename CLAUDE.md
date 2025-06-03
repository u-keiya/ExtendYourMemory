# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Extend Your Memory** is an AI web application that enables users to search across Google Drive files, browser history, and web pages to generate comprehensive reports with citations. The system uses MCP (Model Context Protocol) architecture to integrate multiple data sources.

## System Architecture

This is a multi-component system with:
- **Frontend**: Next.js 14 with App Router
- **Backend**: FastAPI with Pydantic v2
- **MCP Server**: Custom MCP tools for Google Drive, Chrome History, and Mistral OCR
- **Vector Database**: FAISS for local vector storage
- **LLM**: Gemini 2.5 Flash
- **RAG Pipeline**: LangChain with FAISS for vector search

## Key Technical Components

### MCP (Model Context Protocol) Implementation
- Uses `langchain-mcp-adapters` for LangChain integration
- Custom MCP tools: Google Drive search, Chrome history search, Mistral OCR for PDF processing
- MCP server built with FastMCP framework

### RAG Processing Pipeline
1. **Keyword Generation**: LLM generates search keywords from user query
2. **MCP Search**: Multi-source search via Google Drive and Chrome history tools
3. **Document Processing**: Text splitting with support for Markdown headers
4. **Vectorization**: Uses Google's embedding-004 model with FAISS
5. **Semantic Search**: MMR (Maximal Marginal Relevance) search for relevance
6. **Report Generation**: Structured report with citations and sources

### WebSocket Integration
- Real-time progress updates during search and processing
- Step-by-step visibility into: keyword generation, MCP search, vectorization, RAG search, report generation

## Development Environment

### Docker Configuration
Multi-service setup with:
- `mcp-server`: Custom MCP server (port 8501)
- `backend`: FastAPI application (port 8000)  
- `frontend`: Next.js application (port 3000)

### Environment Variables Required
- `GOOGLE_DRIVE_API_KEY`: For Google Drive access
- `CHROME_API_KEY`: For Chrome history access
- `MISTRAL_OCR_API_KEY`: For PDF OCR processing
- `GOOGLE_API_KEY`: For embeddings

## Security Considerations
- Users manage their own API keys
- Chrome history access requires explicit user permission
- Minimal Google Drive access scope
- FAISS vector store data can be periodically cleared
- API keys encrypted in local storage, temporary server-side memory only

## Future Extensions
- Additional MCP tools: Slack, Notion, local file search
- Local LLM options and fine-tuning capabilities
- Interactive search result visualization
- Real-time collaborative report editing

## Development Status
⚠️ **Note**: This project is currently in the specification phase. The description.md contains the complete technical specification and architecture design, but actual implementation files have not yet been created.