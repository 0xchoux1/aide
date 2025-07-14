# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIDE (Autonomous Intelligent Development Environment) is a self-learning AI assistant for infrastructure engineering tasks. The system is built around **Claude Code CLI integration** as its primary AI backend, implementing a production-ready system with Phase 3.3 completed features including self-improvement, optimization, and monitoring capabilities.

## Essential Commands

### Development Environment Setup
```bash
# Setup virtual environment and dependencies
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Main CLI Interface (Production Ready)
```bash
# System initialization and status
python cli.py init
python cli.py status

# AI agent interactions
python cli.py agent ai --query "システムの最適化を実行してください"
python cli.py agent learning --action start
python cli.py agent coordination --action orchestrate

# Learning functionality
python cli.py learn start
python cli.py learn status
python cli.py learn stop
```

### Testing
```bash
# Run all tests with coverage
python -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Run specific test categories
python -m pytest tests/unit/ -v
python -m pytest tests/integration/ -v  
python -m pytest tests/performance/ -v

# Run individual test files
python -m pytest tests/unit/test_base_agent.py -v
python -m pytest tests/integration/test_full_system_integration.py -v
```

### Demo Scripts
```bash
# System demonstrations
python demo.py                    # Basic agent demo
python demo_phase2.py            # Multi-agent with RAG
python demo_rag_system.py        # RAG system demo
python demo_self_improvement.py  # Self-improvement demo
```

## Architecture Overview

### Claude Code Integration (Core AI Backend)

The system's architecture is built around **Claude Code CLI** as the primary AI engine:

- **Claude Code Client** (`src/llm/claude_code_client.py`): Direct CLI interface to Claude Code
- **LLM Interface** (`src/llm/llm_interface.py`): Unified abstraction for AI interactions
- **Authentication**: Uses `claude auth` command (no API keys in environment variables)
- **Execution Pattern**: Subprocess calls to `claude` command with file-based prompts

### Multi-Layered System Architecture

#### 1. Agent Layer (`src/agents/`)
- **BaseAgent**: Foundation for all AI agents with memory and learning integration
- **CrewAgents**: Multi-agent coordination using CrewAI framework
- Agents leverage Claude Code for reasoning and decision-making

#### 2. Knowledge Management (`src/rag/`, `src/memory/`)
- **Vector Store**: ChromaDB integration for semantic search
- **Knowledge Base**: Persistent storage of learned information
- **RAG System**: Retrieval-Augmented Generation for context-aware responses
- **Short-term Memory**: Session-based context management

#### 3. Self-Improvement System (`src/self_improvement/`)
Complete autonomous improvement pipeline:
- **Diagnostics**: Performance monitoring and issue detection
- **Improvement Engine**: Opportunity identification and planning
- **Autonomous Implementation**: Code generation and modification
- **Quality Assurance**: Safety checks and human approval workflows

#### 4. Infrastructure Layer
- **Configuration** (`src/config/`): Environment-based configuration management
- **Logging** (`src/logging/`): Structured logging with audit trails
- **Monitoring** (`src/dashboard/`): Real-time metrics and web dashboard
- **Optimization** (`src/optimization/`): Performance profiling and system optimization
- **Resilience** (`src/resilience/`): Error handling, circuit breakers, retry logic

### Key Architectural Patterns

#### Mock Mode vs Production Mode
- **Mock Mode**: Default operation with simulated responses for development/testing
- **Production Mode**: Activated via `AIDE_ENV=production` with real Claude Code integration
- **Graceful Degradation**: System continues operating when Claude Code unavailable

#### Async-First Design
- Non-blocking operations throughout the system
- Connection pooling and task scheduling
- Memory optimization with object pools

#### Configuration-Driven Behavior
- YAML-based configuration with environment profiles
- Runtime configuration updates
- Extensive customization options via `.env` files

## Development Guidelines

### Production Environment Setup

To transition from mock mode to production:

1. **Ensure Claude Code CLI is available**: `claude --version`
2. **Authenticate with Claude**: `claude auth`
3. **Configure environment**: Copy `.env.example` to `.env` and set `AIDE_ENV=production`
4. **No API keys required**: Claude Code CLI handles authentication internally

### Testing Strategy

The system employs comprehensive testing:
- **Unit Tests**: Individual component verification
- **Integration Tests**: Full system workflow testing
- **Performance Tests**: Benchmarking and optimization verification
- **Mock Integration**: Extensive mocking for reliable CI/CD

### Code Organization Principles

- **Modular Architecture**: Independent, testable components
- **Interface-Driven Design**: Abstract interfaces for major subsystems
- **Safety-First**: Multiple approval gates for autonomous operations
- **Observability**: Comprehensive logging and metrics throughout

### Working with Self-Improvement Features

When modifying self-improvement capabilities:
1. All changes require safety verification in `quality_assurance.py`
2. Human approval workflows must be maintained
3. Rollback capabilities are essential
4. Comprehensive audit logging is mandatory

### Adding New Components

For new functionality:
1. Add configuration in `src/config/defaults.py`
2. Implement tests in appropriate `tests/` subdirectory
3. Add CLI commands in `src/cli/commands.py` if user-facing
4. Update metrics collection if relevant
5. Consider integration with self-improvement system

## Current System Status

### Completed (Phase 3.3)
- ✅ Claude Code CLI integration with robust error handling
- ✅ Complete self-improvement pipeline with safety checks
- ✅ Production-ready CLI interface with mock/production modes
- ✅ Comprehensive monitoring and optimization systems
- ✅ Full test coverage including integration and performance tests
- ✅ Web dashboard with real-time metrics
- ✅ Resilience patterns (circuit breakers, retry logic, fallbacks)

### Key Production Features
- **Dual CLI System**: `cli.py` (production) and `src/cli.py` (internal)
- **Environment Detection**: Automatic mock/production mode switching
- **Health Monitoring**: System health checks and automated recovery
- **Performance Optimization**: Memory management, async processing, caching

The system represents a mature, production-ready AI assistant with autonomous improvement capabilities, built specifically for infrastructure engineering tasks using Claude Code as its AI reasoning engine.