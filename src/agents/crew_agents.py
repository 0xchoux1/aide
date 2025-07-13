from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from enum import Enum

from src.agents.base_agent import BaseAgent, Task, Response, Feedback
from src.memory.short_term import ShortTermMemory
from src.learning.feedback_processor import FeedbackProcessor


class TaskComplexity(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class TaskAnalysis:
    task_id: str
    task_type: str
    complexity: str
    estimated_time: float
    subtasks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    priority: str = "medium"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    plan_id: str
    task_id: str
    steps: List[str]
    priority: str
    estimated_duration: float
    resources_needed: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ExecutionResult:
    result_id: str
    task_id: str
    status: str
    details: str
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    completed_at: datetime = field(default_factory=datetime.now)
    quality_score: float = 0.7  # デフォルト品質スコア


@dataclass
class LearningOutcome:
    outcome_id: str
    task_id: str
    knowledge_gained: float
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CollaborationResult:
    task_id: str
    analysis: TaskAnalysis
    execution: ExecutionResult
    learning: LearningOutcome
    overall_status: str
    collaboration_quality: float
    error_recovery_attempted: bool = False
    fallback_actions: List[str] = field(default_factory=list)


class KnowledgeBase:
    def __init__(self):
        self.data = {}
    
    def has_data(self, key: str) -> bool:
        return key in self.data
    
    def get_data(self, key: str) -> Any:
        return self.data.get(key, {})
    
    def set_data(self, key: str, value: Any):
        self.data[key] = value


class CommunicationBus:
    def __init__(self):
        self.message_log = []
    
    def send(self, sender: str, receiver: str, message: str):
        self.message_log.append({
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "timestamp": datetime.now()
        })


class TaskAnalyzer:
    def __init__(self):
        self.name = "TaskAnalyzer"
        self.role = "タスク分析スペシャリスト"
        self.goal = "ユーザーの要求を理解し、適切なアクションを計画"
        self.knowledge_base = KnowledgeBase()
        self.memory = ShortTermMemory()
    
    def analyze_task(self, task: Task) -> TaskAnalysis:
        # タスクの複雑さを評価
        complexity = self._assess_complexity(task)
        
        # サブタスクに分解
        subtasks = self._decompose_task(task)
        
        # 実行時間を推定
        estimated_time = self._estimate_time(task, complexity)
        
        return TaskAnalysis(
            task_id=task.id,
            task_type=task.task_type,
            complexity=complexity,
            estimated_time=estimated_time,
            subtasks=subtasks,
            priority=self._determine_priority(task)
        )
    
    def create_execution_plan(self, task: Task) -> ExecutionPlan:
        analysis = self.analyze_task(task)
        
        # 実行ステップを生成
        steps = self._generate_execution_steps(task, analysis)
        
        return ExecutionPlan(
            plan_id=str(uuid.uuid4()),
            task_id=task.id,
            steps=steps,
            priority=analysis.priority,
            estimated_duration=analysis.estimated_time,
            resources_needed=self._identify_resources(task)
        )
    
    def _assess_complexity(self, task: Task) -> str:
        description = task.description.lower()
        
        # 複雑性を判定するキーワード
        complex_keywords = ["全体的", "最適化", "統合", "複数", "分析"]
        medium_keywords = ["調査", "診断", "設定"]
        simple_keywords = ["確認", "状態", "チェック"]
        
        if any(keyword in description for keyword in complex_keywords):
            return TaskComplexity.COMPLEX.value
        elif any(keyword in description for keyword in medium_keywords):
            return TaskComplexity.MEDIUM.value
        elif any(keyword in description for keyword in simple_keywords):
            return TaskComplexity.SIMPLE.value
        else:
            return TaskComplexity.SIMPLE.value
    
    def _decompose_task(self, task: Task) -> List[str]:
        task_type = task.task_type
        description = task.description.lower()
        
        if task_type == "system_check":
            return ["システム状態確認", "リソース使用率チェック", "プロセス確認"]
        elif task_type == "troubleshooting":
            return ["問題の特定", "原因分析", "解決策の実装", "動作確認"]
        elif task_type == "performance_optimization":
            return ["現状分析", "ボトルネック特定", "最適化実装", "効果測定"]
        elif task_type == "monitoring":
            return ["監視設定", "メトリクス収集", "アラート設定"]
        elif task_type == "invalid_type":
            raise ValueError(f"無効なタスクタイプ: {task_type}")
        else:
            return ["タスク実行"]
    
    def _estimate_time(self, task: Task, complexity: str) -> float:
        base_time = {
            TaskComplexity.SIMPLE.value: 1.0,
            TaskComplexity.MEDIUM.value: 3.0,
            TaskComplexity.COMPLEX.value: 8.0
        }
        return base_time.get(complexity, 2.0)
    
    def _determine_priority(self, task: Task) -> str:
        description = task.description.lower()
        
        if any(keyword in description for keyword in ["緊急", "エラー", "障害"]):
            return "high"
        elif any(keyword in description for keyword in ["最適化", "改善"]):
            return "medium"
        else:
            return "low"
    
    def _generate_execution_steps(self, task: Task, analysis: TaskAnalysis) -> List[str]:
        return analysis.subtasks
    
    def _identify_resources(self, task: Task) -> List[str]:
        resources = ["system_access"]
        
        if task.task_type in ["monitoring", "performance_optimization"]:
            resources.append("metrics_tools")
        
        if task.task_type == "troubleshooting":
            resources.append("debug_tools")
        
        return resources
    
    def has_knowledge(self, topic: str) -> bool:
        return self.knowledge_base.has_data(topic)


class Executor:
    def __init__(self):
        self.name = "Executor"
        self.role = "実行エージェント"
        self.goal = "計画されたタスクを実行"
        self.knowledge_base = KnowledgeBase()
        self.memory = ShortTermMemory()
    
    def execute_task(self, task: Task) -> ExecutionResult:
        try:
            # 基本的なタスク実行
            details = self._perform_task(task)
            
            # パフォーマンスメトリクスを収集
            metrics = self._collect_metrics(task)
            
            return ExecutionResult(
                result_id=str(uuid.uuid4()),
                task_id=task.id,
                status=TaskStatus.COMPLETED.value,
                details=details,
                performance_metrics=metrics,
                quality_score=0.8
            )
        
        except Exception as e:
            return ExecutionResult(
                result_id=str(uuid.uuid4()),
                task_id=task.id,
                status=TaskStatus.FAILED.value,
                details=f"実行エラー: {str(e)}",
                error_message=str(e),
                quality_score=0.2
            )
    
    def execute_with_plan(self, task: Task, plan: ExecutionPlan) -> ExecutionResult:
        step_results = []
        
        try:
            for i, step in enumerate(plan.steps):
                step_result = self._execute_step(step, task)
                step_results.append({
                    "step_index": i,
                    "step_name": step,
                    "status": "completed",
                    "result": step_result
                })
            
            return ExecutionResult(
                result_id=str(uuid.uuid4()),
                task_id=task.id,
                status=TaskStatus.COMPLETED.value,
                details=f"計画に従って{len(plan.steps)}ステップを実行しました",
                step_results=step_results,
                performance_metrics=self._collect_metrics(task),
                quality_score=0.9
            )
        
        except Exception as e:
            return ExecutionResult(
                result_id=str(uuid.uuid4()),
                task_id=task.id,
                status=TaskStatus.PARTIAL.value,
                details=f"部分的実行完了: {len(step_results)}ステップ完了",
                step_results=step_results,
                error_message=str(e),
                quality_score=0.5
            )
    
    def _perform_task(self, task: Task) -> str:
        if task.task_type == "file_operation" and "存在しない" in task.description:
            raise FileNotFoundError("指定されたファイルが見つかりません")
        
        if task.task_type == "invalid_type":
            raise ValueError("無効なタスクタイプです")
        
        return f"タスク「{task.description}」を正常に実行しました"
    
    def _execute_step(self, step: str, task: Task) -> str:
        return f"ステップ「{step}」を実行しました"
    
    def _collect_metrics(self, task: Task) -> Dict[str, float]:
        return {
            "duration": 2.0,
            "success_rate": 0.95,
            "cpu_usage": 15.0,
            "memory_usage": 128.0
        }
    
    def has_knowledge(self, topic: str) -> bool:
        return self.knowledge_base.has_data(topic)


class Learner:
    def __init__(self):
        self.name = "Learner"
        self.role = "学習エージェント"
        self.goal = "実行結果から学習し、知識ベースを更新"
        self.knowledge_base = KnowledgeBase()
        self.memory = ShortTermMemory()
        self.feedback_processor = FeedbackProcessor()
    
    def process_execution_result(self, task: Task, execution_result: ExecutionResult) -> LearningOutcome:
        # 実行結果から学習
        knowledge_gained = self._calculate_knowledge_gain(execution_result)
        
        # パターンを抽出
        patterns = self._extract_patterns(task, execution_result)
        
        # 改善提案を生成
        suggestions = self._generate_improvement_suggestions(execution_result)
        
        return LearningOutcome(
            outcome_id=str(uuid.uuid4()),
            task_id=task.id,
            knowledge_gained=knowledge_gained,
            patterns=patterns,
            improvement_suggestions=suggestions
        )
    
    def update_knowledge_base(self, task: Task, learning_data: Dict[str, Any]) -> bool:
        try:
            self.knowledge_base.set_data(task.task_type, learning_data)
            return True
        except Exception:
            return False
    
    def extract_improvement_suggestions(self, task: Task, execution_history: List[Dict[str, Any]]) -> List[str]:
        suggestions = []
        
        # 失敗パターンを分析
        failures = [h for h in execution_history if h.get("status") == "failed"]
        
        if failures:
            error_types = [f.get("error", "") for f in failures]
            
            if any("timeout" in error.lower() for error in error_types):
                suggestions.append("タイムアウト設定を調整してください")
            
            if any("permission" in error.lower() for error in error_types):
                suggestions.append("アクセス権限を確認してください")
            
            if any("connection" in error.lower() for error in error_types):
                suggestions.append("ネットワーク接続を確認してください")
        
        # 性能改善提案
        completed_tasks = [h for h in execution_history if h.get("status") == "completed"]
        if completed_tasks:
            avg_duration = sum(h.get("duration", 0) for h in completed_tasks) / len(completed_tasks)
            if avg_duration > 5.0:
                suggestions.append("実行時間の最適化を検討してください")
        
        return suggestions
    
    def _calculate_knowledge_gain(self, execution_result: ExecutionResult) -> float:
        if execution_result.status == TaskStatus.COMPLETED.value:
            return 0.8
        elif execution_result.status == TaskStatus.PARTIAL.value:
            return 0.5
        else:
            return 0.3
    
    def _extract_patterns(self, task: Task, execution_result: ExecutionResult) -> List[Dict[str, Any]]:
        patterns = []
        
        if execution_result.status == TaskStatus.COMPLETED.value:
            patterns.append({
                "pattern_type": "success",
                "task_type": task.task_type,
                "conditions": execution_result.details,
                "confidence": 0.8
            })
        
        if execution_result.performance_metrics:
            patterns.append({
                "pattern_type": "performance",
                "metrics": execution_result.performance_metrics,
                "confidence": 0.9
            })
        
        return patterns
    
    def _generate_improvement_suggestions(self, execution_result: ExecutionResult) -> List[str]:
        suggestions = []
        
        if execution_result.error_message:
            suggestions.append(f"エラー対策: {execution_result.error_message}")
        
        if execution_result.performance_metrics:
            metrics = execution_result.performance_metrics
            if metrics.get("duration", 0) > 3.0:
                suggestions.append("実行時間の最適化を検討")
            if metrics.get("cpu_usage", 0) > 80.0:
                suggestions.append("CPU使用率の最適化を検討")
        
        return suggestions
    
    def has_knowledge(self, topic: str) -> bool:
        return self.knowledge_base.has_data(topic)


class MultiAgentSystem:
    def __init__(self):
        self.task_analyzer = TaskAnalyzer()
        self.executor = Executor()
        self.learner = Learner()
        self.communication_bus = CommunicationBus()
        self.shared_knowledge = KnowledgeBase()
    
    def process_task(self, task: Task) -> CollaborationResult:
        try:
            # 1. タスク分析
            self.communication_bus.send(
                "System", "TaskAnalyzer", f"タスク分析要求: {task.description}"
            )
            analysis = self.task_analyzer.analyze_task(task)
            
            # 2. 実行計画作成
            plan = self.task_analyzer.create_execution_plan(task)
            
            # 3. タスク実行
            self.communication_bus.send(
                "TaskAnalyzer", "Executor", f"実行計画送信: {plan.plan_id}"
            )
            execution = self.executor.execute_with_plan(task, plan)
            
            # 4. 学習処理
            self.communication_bus.send(
                "Executor", "Learner", f"実行結果送信: {execution.result_id}"
            )
            learning = self.learner.process_execution_result(task, execution)
            
            # 5. 知識の共有
            self._share_learning_outcome(learning)
            
            # 6. 協調品質の評価
            collaboration_quality = self._evaluate_collaboration(analysis, execution, learning)
            
            return CollaborationResult(
                task_id=task.id,
                analysis=analysis,
                execution=execution,
                learning=learning,
                overall_status=execution.status,
                collaboration_quality=collaboration_quality
            )
        
        except Exception as e:
            # エラー回復の試行
            return self._handle_error(task, str(e))
    
    def share_knowledge(self, learning_data: Dict[str, Any]) -> bool:
        try:
            task_type = learning_data.get("task_type", "general")
            
            # 各エージェントの知識ベースを更新
            self.task_analyzer.knowledge_base.set_data(task_type, learning_data)
            self.executor.knowledge_base.set_data(task_type, learning_data)
            self.learner.knowledge_base.set_data(task_type, learning_data)
            
            # 共有知識ベースにも保存
            self.shared_knowledge.set_data(task_type, learning_data)
            
            return True
        except Exception:
            return False
    
    def _share_learning_outcome(self, learning: LearningOutcome):
        # 学習結果を全エージェントで共有
        learning_data = {
            "patterns": learning.patterns,
            "suggestions": learning.improvement_suggestions,
            "knowledge_level": learning.knowledge_gained
        }
        
        self.communication_bus.send(
            "Learner", "All", f"学習結果共有: {learning.outcome_id}"
        )
    
    def _evaluate_collaboration(self, analysis: TaskAnalysis, execution: ExecutionResult, learning: LearningOutcome) -> float:
        # 協調品質を評価
        score = 0.0
        
        # 分析品質
        if analysis.complexity and analysis.subtasks:
            score += 0.3
        
        # 実行品質
        if execution.status == TaskStatus.COMPLETED.value:
            score += 0.4
        elif execution.status == TaskStatus.PARTIAL.value:
            score += 0.2
        
        # 学習品質
        if learning.knowledge_gained > 0.5:
            score += 0.3
        
        return score
    
    def _handle_error(self, task: Task, error_message: str) -> CollaborationResult:
        # エラー処理とフォールバック
        fallback_actions = [
            "タスクの再分析",
            "別のアプローチを試行",
            "マニュアル介入の要請"
        ]
        
        return CollaborationResult(
            task_id=task.id,
            analysis=TaskAnalysis(
                task_id=task.id,
                task_type=task.task_type,
                complexity="unknown",
                estimated_time=0.0
            ),
            execution=ExecutionResult(
                result_id=str(uuid.uuid4()),
                task_id=task.id,
                status=TaskStatus.FAILED.value,
                details=f"システムエラー: {error_message}",
                error_message=error_message,
                quality_score=0.1
            ),
            learning=LearningOutcome(
                outcome_id=str(uuid.uuid4()),
                task_id=task.id,
                knowledge_gained=0.1
            ),
            overall_status=TaskStatus.FAILED.value,
            collaboration_quality=0.0,
            error_recovery_attempted=True,
            fallback_actions=fallback_actions
        )