from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from collections import defaultdict


@dataclass
class ImprovementPattern:
    pattern_type: str
    improvement_type: str
    condition: str
    action: str
    confidence: float
    usage_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)


class FeedbackProcessor:
    def __init__(self):
        self.patterns: Dict[str, List[ImprovementPattern]] = defaultdict(list)
        self.feedback_history: List[Dict[str, Any]] = []
    
    def process_feedback(self, feedback):
        # フィードバックを履歴に保存
        feedback_data = {
            'task_type': feedback.task.task_type,
            'rating': feedback.rating,
            'improvement_suggestion': feedback.improvement_suggestion,
            'response_quality': feedback.response.quality_score,
            'created_at': feedback.created_at.isoformat()
        }
        self.feedback_history.append(feedback_data)
        
        # 改善パターンを抽出
        patterns = self._extract_patterns(feedback)
        
        # パターンを更新
        for pattern in patterns:
            self._update_pattern(pattern, feedback.task.task_type)
    
    def extract_improvement_patterns(self, feedback) -> List[Dict[str, Any]]:
        patterns = []
        
        # 評価が低い場合の改善パターン
        if feedback.rating < 4:
            suggestion = feedback.improvement_suggestion.lower()
            
            if '詳細' in suggestion or 'detail' in suggestion:
                patterns.append({
                    'improvement_type': 'add_details',
                    'trigger': 'low_rating_needs_details',
                    'action': 'include_detailed_metrics',
                    'confidence': 0.8
                })
            
            if '履歴' in suggestion or 'history' in suggestion or '過去' in suggestion:
                patterns.append({
                    'improvement_type': 'add_context',
                    'trigger': 'low_rating_needs_context',
                    'action': 'reference_historical_data',
                    'confidence': 0.7
                })
            
            if '正確' in suggestion or '精度' in suggestion:
                patterns.append({
                    'improvement_type': 'improve_accuracy',
                    'trigger': 'low_rating_accuracy',
                    'action': 'verify_information',
                    'confidence': 0.9
                })
        
        return patterns
    
    def get_patterns(self, task_type: str) -> List[Dict[str, Any]]:
        patterns = self.patterns.get(task_type, [])
        
        # 使用回数と信頼度でソート
        sorted_patterns = sorted(
            patterns,
            key=lambda p: (p.confidence, p.usage_count),
            reverse=True
        )
        
        # 辞書形式で返す
        return [
            {
                'improvement_type': pattern.improvement_type,
                'condition': pattern.condition,
                'action': pattern.action,
                'confidence': pattern.confidence,
                'usage_count': pattern.usage_count
            }
            for pattern in sorted_patterns
        ]
    
    def _extract_patterns(self, feedback) -> List[ImprovementPattern]:
        patterns = []
        suggestion = feedback.improvement_suggestion.lower()
        
        if '詳細' in suggestion:
            patterns.append(ImprovementPattern(
                pattern_type='response_enhancement',
                improvement_type='add_details',
                condition='user_requests_more_details',
                action='include_comprehensive_information',
                confidence=0.8
            ))
        
        if '速度' in suggestion or '早く' in suggestion:
            patterns.append(ImprovementPattern(
                pattern_type='performance_improvement',
                improvement_type='increase_speed',
                condition='user_requests_faster_response',
                action='optimize_processing_time',
                confidence=0.7
            ))
        
        if '正確' in suggestion or '間違い' in suggestion:
            patterns.append(ImprovementPattern(
                pattern_type='accuracy_improvement',
                improvement_type='improve_accuracy',
                condition='user_reports_inaccuracy',
                action='verify_information_sources',
                confidence=0.9
            ))
        
        return patterns
    
    def _update_pattern(self, pattern: ImprovementPattern, task_type: str):
        existing_patterns = self.patterns[task_type]
        
        # 類似パターンがあるかチェック
        for existing_pattern in existing_patterns:
            if (existing_pattern.improvement_type == pattern.improvement_type and
                existing_pattern.condition == pattern.condition):
                # 既存パターンを更新
                existing_pattern.usage_count += 1
                existing_pattern.confidence = min(
                    existing_pattern.confidence + 0.1,
                    1.0
                )
                return
        
        # 新しいパターンを追加
        self.patterns[task_type].append(pattern)
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        stats = {
            'total_feedback': len(self.feedback_history),
            'patterns_by_type': {},
            'average_ratings': {},
            'improvement_trends': {}
        }
        
        # タスクタイプ別のパターン数
        for task_type, patterns in self.patterns.items():
            stats['patterns_by_type'][task_type] = len(patterns)
        
        # タスクタイプ別の平均評価
        ratings_by_type = defaultdict(list)
        for feedback in self.feedback_history:
            ratings_by_type[feedback['task_type']].append(feedback['rating'])
        
        for task_type, ratings in ratings_by_type.items():
            stats['average_ratings'][task_type] = sum(ratings) / len(ratings)
        
        return stats
    
    def export_knowledge(self) -> Dict[str, Any]:
        return {
            'patterns': {
                task_type: [
                    {
                        'pattern_type': p.pattern_type,
                        'improvement_type': p.improvement_type,
                        'condition': p.condition,
                        'action': p.action,
                        'confidence': p.confidence,
                        'usage_count': p.usage_count,
                        'created_at': p.created_at.isoformat()
                    }
                    for p in patterns
                ]
                for task_type, patterns in self.patterns.items()
            },
            'feedback_history': self.feedback_history
        }