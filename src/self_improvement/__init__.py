"""
AIDE 自律改善システム

自己診断、改善計画、自動実装を行う自律改善システム
"""

from .diagnostics import (
    SystemDiagnostics,
    PerformanceMonitor,
    CodeQualityAnalyzer,
    LearningEffectivenessEvaluator
)

from .improvement_engine import (
    ImprovementEngine,
    OpportunityIdentifier,
    PriorityOptimizer,
    RoadmapGenerator
)

from .autonomous_implementation import (
    AutonomousImplementation,
    CodeGenerator,
    TestAutomation,
    DeploymentManager
)

from .quality_assurance import (
    QualityAssurance,
    SafetyChecker,
    HumanApprovalGate,
    QualityMetrics
)

__all__ = [
    # Diagnostics
    'SystemDiagnostics',
    'PerformanceMonitor', 
    'CodeQualityAnalyzer',
    'LearningEffectivenessEvaluator',
    
    # Improvement Engine
    'ImprovementEngine',
    'OpportunityIdentifier',
    'PriorityOptimizer', 
    'RoadmapGenerator',
    
    # Autonomous Implementation
    'AutonomousImplementation',
    'CodeGenerator',
    'TestAutomation',
    'DeploymentManager',
    
    # Quality Assurance
    'QualityAssurance',
    'SafetyChecker',
    'HumanApprovalGate',
    'QualityMetrics'
]