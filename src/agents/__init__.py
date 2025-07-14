"""
AIDE エージェント群

AIエージェントと関連コンポーネント
"""

from .base_agent import BaseAgent
from .remote_agent import RemoteAgent, InvestigationResult, ServerGroup

# try:
#     from .crew_agents import (
#         DiagnosisAgent,
#         ImprovementAgent, 
#         ImplementationAgent,
#         QualityAssuranceAgent,
#         get_crew_agents
#     )
#     crew_agents_available = True
# except ImportError:
#     crew_agents_available = False

__all__ = [
    'BaseAgent',
    'RemoteAgent',
    'InvestigationResult',
    'ServerGroup'
    # 'DiagnosisAgent',
    # 'ImprovementAgent',
    # 'ImplementationAgent', 
    # 'QualityAssuranceAgent',
    # 'get_crew_agents'
]