# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIDE (自律学習型AIアシスタント) is a self-learning AI assistant for infrastructure engineering and SRE tasks. The system is built in phases, with Phase 3.2 completed, implementing a comprehensive self-improvement architecture with real-time monitoring, optimization, and autonomous enhancement capabilities.

## Essential Commands

### Development Environment
```bash
# Setup virtual environment and dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Testing
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

# Run specific test files
pytest tests/unit/test_self_improvement_diagnostics.py -v
pytest tests/integration/test_self_improvement_integration.py -v

# Run tests for specific modules
pytest tests/unit/test_base_agent.py -v
pytest tests/unit/test_rag_system.py -v
```

### Demos and Execution
```bash
# Phase 1 demo (basic agent)
python demo.py

# Phase 2 demo (multi-agent with RAG)  
python demo_phase2.py

# RAG system demo
python demo_rag_system.py
```

### CLI Interface
```bash
# Interactive mode
python -m src.cli.cli_manager interactive

# Configuration management
python -m src.cli.cli_manager config --list
python -m src.cli.cli_manager config --set key=value

# Dashboard and monitoring
python -m src.cli.cli_manager dashboard start
python -m src.cli.cli_manager metrics
```

## Architecture Overview

### Phase Structure
The system is architected in three main phases:
- **Phase 1**: Basic learning agent with short-term memory (completed)
- **Phase 2**: Multi-agent system with RAG integration (completed) 
- **Phase 3**: Self-improvement capabilities (Phase 3.2 completed)

### Core Architectural Patterns

#### Multi-Agent Coordination
The system uses CrewAI for multi-agent coordination with three specialized agents:
- **Analysis Agent**: Task analysis and planning
- **Execution Agent**: Task execution and tool usage
- **Learning Agent**: Knowledge extraction and storage

#### RAG System Integration
Knowledge management through:
- **ChromaDB**: Vector database for knowledge storage
- **Embedding Model**: all-MiniLM-L6-v2 for text embeddings
- **Dynamic Learning**: Real-time knowledge updates from task execution

#### Self-Improvement Architecture (Phase 3)
Implemented a comprehensive self-improvement system with four core modules:

1. **Diagnostics System** (`src/self_improvement/diagnostics.py`)
   - Performance monitoring and bottleneck detection
   - Code quality analysis and metrics collection
   - Learning effectiveness evaluation

2. **Improvement Engine** (`src/self_improvement/improvement_engine.py`)
   - Opportunity identification and priority optimization
   - Automated roadmap generation with Claude Code integration
   - ROI-based improvement planning

3. **Autonomous Implementation** (`src/self_improvement/autonomous_implementation.py`)
   - Code generation and modification capabilities
   - Test automation and coverage improvement
   - Deployment management with safety checks

4. **Quality Assurance** (`src/self_improvement/quality_assurance.py`)
   - Multi-layer safety verification
   - Human approval workflows for critical changes
   - Comprehensive quality metrics and trend analysis

#### Supporting Infrastructure (Phase 3.2)

**Configuration Management** (`src/config/`)
- Environment-based profiles (development, testing, production)
- YAML-based configuration with validation
- Runtime configuration updates

**CLI System** (`src/cli/`)
- Interactive command interface with auto-completion
- Command routing and execution framework
- Formatted output and error handling

**Logging & Monitoring** (`src/logging/`, `src/dashboard/`)
- Structured logging with audit trails
- Real-time metrics collection and visualization
- Web-based dashboard with health monitoring

**Performance Optimization** (`src/optimization/`)
- Memory optimization with object/memory pools
- Performance profiling and bottleneck analysis
- Async processing with task scheduling and connection pooling

### Key Integrations

#### Claude Code Integration
The system leverages Claude Code for:
- Automated code generation and modification
- Test case generation and improvement
- Documentation generation
- Code review and quality analysis

#### External Dependencies
- **ChromaDB**: Vector storage and similarity search
- **CrewAI**: Multi-agent orchestration framework
- **pytest**: Comprehensive testing framework
- **pydantic**: Data validation and type safety
- **psutil**: System monitoring (optional, with graceful degradation)

## Development Guidelines

### Test-Driven Development
- Follow Red-Green-Refactor cycle
- Maintain high test coverage (current: 85%+)
- Write tests before implementation
- Use comprehensive mocking for external dependencies

### Code Organization Principles
- **Modular Design**: Each component operates independently
- **Configuration-Driven**: Flexible behavior through config files
- **Graceful Degradation**: System continues operating when optional dependencies unavailable
- **Async-First**: Non-blocking operations where possible

### Phase 3 Development Considerations
- All self-improvement operations require safety checks
- Human approval gates for critical system changes
- Comprehensive logging for audit and debugging
- Rollback capabilities for all automated changes

### Adding New Functionality
When extending the system:
1. Add configuration options in `src/config/defaults.py`
2. Implement comprehensive tests in `tests/unit/` and `tests/integration/`
3. Add CLI commands in `src/cli/commands.py` if user-facing
4. Update metrics collection in `src/dashboard/metrics_collector.py`
5. Consider self-improvement integration opportunities

## Current Status

### Completed Components (Phase 3.2)
- ✅ Self-improvement foundation with 4 core modules (3,304 lines)
- ✅ Comprehensive test suite (5 test files covering all modules)
- ✅ Configuration management with environment profiles
- ✅ Full CLI interface with interactive mode
- ✅ Structured logging and audit systems
- ✅ Real-time metrics dashboard
- ✅ Memory and performance optimization systems
- ✅ Async processing optimization

### Ready for Phase 3.3
The system is prepared for Phase 3.3 (Integration & Optimization) which includes:
- Full component integration and end-to-end testing
- Performance benchmarking and optimization
- Production deployment preparation

The codebase represents a mature, production-ready self-learning AI system with comprehensive testing, monitoring, and self-improvement capabilities.