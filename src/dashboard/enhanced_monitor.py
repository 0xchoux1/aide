"""
AIDE 強化監視・アラートシステム

リアルタイム監視、アラート、エラーハンドリング統合機能
"""

import time
import threading
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import json

from ..config import get_config_manager
from ..logging import get_logger, get_audit_logger
from ..resilience.error_handler import get_error_handler, ErrorSeverity
from ..resilience.circuit_breaker import get_circuit_breaker_manager
from ..resilience.retry_manager import get_retry_manager
from ..resilience.fallback_system import get_fallback_system
from .metrics_collector import get_metrics_collector
from .realtime_monitor import get_realtime_monitor


class HealthStatus(Enum):
    """ヘルス状態"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class MonitoringMode(Enum):
    """監視モード"""
    BASIC = "basic"
    ENHANCED = "enhanced"
    FULL = "full"


@dataclass
class SystemHealth:
    """システムヘルス情報"""
    overall_status: HealthStatus
    overall_score: float
    component_health: Dict[str, Dict[str, Any]]
    active_issues: List[Dict[str, Any]]
    recommendations: List[str]
    last_updated: float
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        data = asdict(self)
        data['overall_status'] = self.overall_status.value
        return data


@dataclass
class AlertRule:
    """アラートルール"""
    rule_id: str
    name: str
    description: str
    metric_name: str
    condition: str  # e.g., "> 80", "< 0.5"
    severity: str
    cooldown_minutes: int = 5
    enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return asdict(self)


class EnhancedMonitor:
    """強化監視・アラートシステム"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager or get_config_manager()
        self.logger = get_logger(__name__)
        self.audit_logger = get_audit_logger()
        
        # 外部システム統合
        self.error_handler = get_error_handler()
        self.circuit_breaker_manager = get_circuit_breaker_manager()
        self.retry_manager = get_retry_manager()
        self.fallback_system = get_fallback_system()
        self.metrics_collector = get_metrics_collector()
        self.realtime_monitor = get_realtime_monitor()
        
        # 監視設定
        self.monitoring_mode = MonitoringMode(
            self.config_manager.get("monitoring.mode", "enhanced")
        )
        self.health_check_interval = self.config_manager.get("monitoring.health_check_interval", 30)
        self.metrics_retention_hours = self.config_manager.get("monitoring.metrics_retention_hours", 24)
        
        # システムヘルス
        self.current_health: Optional[SystemHealth] = None
        self.health_history: List[SystemHealth] = []
        self.max_health_history = 100
        
        # カスタムアラートルール
        self.custom_alert_rules: Dict[str, AlertRule] = {}
        self._initialize_custom_rules()
        
        # 監視スレッド
        self.monitor_thread = None
        self.stop_monitoring = threading.Event()
        self.is_monitoring = False
        
        # 統計
        self.monitoring_stats = {
            'total_health_checks': 0,
            'health_status_changes': 0,
            'alerts_generated': 0,
            'errors_detected': 0,
            'circuit_breaker_trips': 0
        }

    def _initialize_custom_rules(self):
        """カスタムアラートルール初期化"""
        custom_rules = [
            AlertRule(
                rule_id="error_rate_high",
                name="エラー率高",
                description="システムエラー率が5%を超えています",
                metric_name="error_rate",
                condition="> 0.05",
                severity="high",
                cooldown_minutes=10
            ),
            
            AlertRule(
                rule_id="circuit_breaker_open",
                name="サーキットブレーカーオープン",
                description="サーキットブレーカーがオープン状態です",
                metric_name="circuit_breaker_open_count",
                condition="> 0",
                severity="critical",
                cooldown_minutes=5
            ),
            
            AlertRule(
                rule_id="retry_rate_high",
                name="リトライ率高",
                description="リトライ率が20%を超えています",
                metric_name="retry_rate",
                condition="> 0.20",
                severity="medium",
                cooldown_minutes=15
            ),
            
            AlertRule(
                rule_id="fallback_usage_high",
                name="フォルバック使用率高",
                description="フォルバック使用率が10%を超えています",
                metric_name="fallback_rate",
                condition="> 0.10",
                severity="medium",
                cooldown_minutes=10
            ),
            
            AlertRule(
                rule_id="health_score_low",
                name="ヘルススコア低下",
                description="システムヘルススコアが60を下回りました",
                metric_name="health_score",
                condition="< 60",
                severity="high",
                cooldown_minutes=5
            )
        ]
        
        for rule in custom_rules:
            self.custom_alert_rules[rule.rule_id] = rule

    def start_monitoring(self):
        """拡張監視開始"""
        if self.is_monitoring:
            self.logger.warning("拡張監視は既に開始されています")
            return
        
        # 基本監視も開始
        self.realtime_monitor.start_monitoring()
        
        # 拡張監視開始
        self.stop_monitoring.clear()
        self.monitor_thread = threading.Thread(
            target=self._enhanced_monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        self.is_monitoring = True
        
        self.logger.info(f"拡張監視開始 (モード: {self.monitoring_mode.value})")
        self.audit_logger.log_system_event("enhanced_monitoring_start", "拡張監視開始")

    def stop_monitoring_system(self):
        """拡張監視停止"""
        if not self.is_monitoring:
            return
        
        self.stop_monitoring.set()
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10.0)
        
        # 基本監視も停止
        self.realtime_monitor.stop_monitoring()
        
        self.is_monitoring = False
        self.logger.info("拡張監視停止")
        self.audit_logger.log_system_event("enhanced_monitoring_stop", "拡張監視停止")

    def _enhanced_monitoring_loop(self):
        """拡張監視ループ"""
        while not self.stop_monitoring.is_set():
            try:
                # システムヘルスチェック
                self._perform_health_check()
                
                # カスタムアラートチェック
                self._check_custom_alerts()
                
                # 統計更新
                self._update_monitoring_stats()
                
                # メトリクスクリーンアップ
                self._cleanup_old_metrics()
                
            except Exception as e:
                self.logger.error(f"拡張監視ループエラー: {str(e)}")
                # エラーハンドリング統合
                self.error_handler.handle_error(
                    e, "enhanced_monitor", "_enhanced_monitoring_loop"
                )
            
            self.stop_monitoring.wait(self.health_check_interval)

    def _perform_health_check(self):
        """システムヘルスチェック実行"""
        self.monitoring_stats['total_health_checks'] += 1
        
        try:
            # 各コンポーネントのヘルス評価
            component_health = self._evaluate_component_health()
            
            # 全体ヘルススコア計算
            overall_score = self._calculate_overall_health_score(component_health)
            overall_status = self._determine_health_status(overall_score)
            
            # アクティブ問題特定
            active_issues = self._identify_active_issues(component_health)
            
            # 推奨事項生成
            recommendations = self._generate_recommendations(component_health, active_issues)
            
            # システムヘルス更新
            new_health = SystemHealth(
                overall_status=overall_status,
                overall_score=overall_score,
                component_health=component_health,
                active_issues=active_issues,
                recommendations=recommendations,
                last_updated=time.time()
            )
            
            # 状態変化検出
            if self.current_health and self.current_health.overall_status != new_health.overall_status:
                self.monitoring_stats['health_status_changes'] += 1
                self.logger.info(
                    f"システムヘルス状態変化: {self.current_health.overall_status.value} -> {new_health.overall_status.value}"
                )
                self.audit_logger.log_system_event(
                    "health_status_change",
                    f"ヘルス状態変化: {new_health.overall_status.value}",
                    health_score=overall_score
                )
            
            self.current_health = new_health
            
            # ヘルス履歴更新
            self.health_history.append(new_health)
            if len(self.health_history) > self.max_health_history:
                self.health_history = self.health_history[-self.max_health_history:]
            
            # メトリクス記録
            self.metrics_collector.record_metric("health_score", overall_score)
            self.metrics_collector.record_metric("active_issues_count", len(active_issues))
            
        except Exception as e:
            self.logger.error(f"ヘルスチェックエラー: {str(e)}")

    def _evaluate_component_health(self) -> Dict[str, Dict[str, Any]]:
        """コンポーネントヘルス評価"""
        component_health = {}
        
        # エラーハンドリングシステム
        try:
            error_stats = self.error_handler.get_error_statistics()
            error_health = self._evaluate_error_handler_health(error_stats)
            component_health['error_handler'] = error_health
        except Exception as e:
            component_health['error_handler'] = {'status': 'unknown', 'error': str(e)}
        
        # サーキットブレーカー
        try:
            circuit_health = self.circuit_breaker_manager.get_health_summary()
            component_health['circuit_breaker'] = {
                'status': 'healthy' if circuit_health['overall_health_rate'] > 80 else 'degraded',
                'health_rate': circuit_health['overall_health_rate'],
                'unhealthy_circuits': circuit_health['unhealthy_circuits']
            }
        except Exception as e:
            component_health['circuit_breaker'] = {'status': 'unknown', 'error': str(e)}
        
        # リトライシステム
        try:
            retry_stats = self.retry_manager.get_statistics()
            retry_health = self._evaluate_retry_health(retry_stats)
            component_health['retry_system'] = retry_health
        except Exception as e:
            component_health['retry_system'] = {'status': 'unknown', 'error': str(e)}
        
        # フォルバックシステム
        try:
            fallback_stats = self.fallback_system.get_statistics()
            fallback_health = self._evaluate_fallback_health(fallback_stats)
            component_health['fallback_system'] = fallback_health
        except Exception as e:
            component_health['fallback_system'] = {'status': 'unknown', 'error': str(e)}
        
        # メトリクス収集
        try:
            metrics_stats = self.metrics_collector.get_collection_stats()
            metrics_health = self._evaluate_metrics_health(metrics_stats)
            component_health['metrics_collector'] = metrics_health
        except Exception as e:
            component_health['metrics_collector'] = {'status': 'unknown', 'error': str(e)}
        
        return component_health

    def _evaluate_error_handler_health(self, error_stats: Dict[str, Any]) -> Dict[str, Any]:
        """エラーハンドラーヘルス評価"""
        total_errors = error_stats['error_stats']['total_errors']
        auto_resolved = error_stats['error_stats']['auto_resolved_errors']
        
        if total_errors == 0:
            status = 'healthy'
            score = 100
        else:
            resolution_rate = auto_resolved / total_errors if total_errors > 0 else 0
            if resolution_rate > 0.8:
                status = 'healthy'
                score = 90
            elif resolution_rate > 0.5:
                status = 'degraded'
                score = 70
            else:
                status = 'unhealthy'
                score = 40
        
        return {
            'status': status,
            'score': score,
            'total_errors': total_errors,
            'auto_resolved_errors': auto_resolved,
            'resolution_rate': auto_resolved / total_errors if total_errors > 0 else 1.0
        }

    def _evaluate_retry_health(self, retry_stats: Dict[str, Any]) -> Dict[str, Any]:
        """リトライシステムヘルス評価"""
        success_rate = retry_stats['success_rate']
        
        if success_rate > 90:
            status = 'healthy'
            score = 95
        elif success_rate > 70:
            status = 'degraded'
            score = 75
        else:
            status = 'unhealthy'
            score = 50
        
        return {
            'status': status,
            'score': score,
            'success_rate': success_rate,
            'total_retries': retry_stats['retry_statistics']['total_retry_attempts']
        }

    def _evaluate_fallback_health(self, fallback_stats: Dict[str, Any]) -> Dict[str, Any]:
        """フォルバックシステムヘルス評価"""
        success_rate = fallback_stats['success_rate']
        total_fallbacks = fallback_stats['fallback_statistics']['total_fallbacks']
        
        if total_fallbacks == 0:
            status = 'healthy'
            score = 100
        elif success_rate > 95:
            status = 'healthy'
            score = 90
        elif success_rate > 80:
            status = 'degraded'
            score = 70
        else:
            status = 'unhealthy'
            score = 50
        
        return {
            'status': status,
            'score': score,
            'success_rate': success_rate,
            'total_fallbacks': total_fallbacks
        }

    def _evaluate_metrics_health(self, metrics_stats: Dict[str, Any]) -> Dict[str, Any]:
        """メトリクス収集ヘルス評価"""
        is_collecting = metrics_stats['is_collecting']
        total_metrics = metrics_stats['total_metrics']
        
        if is_collecting and total_metrics > 0:
            status = 'healthy'
            score = 95
        elif is_collecting:
            status = 'degraded'
            score = 75
        else:
            status = 'unhealthy'
            score = 30
        
        return {
            'status': status,
            'score': score,
            'is_collecting': is_collecting,
            'total_metrics': total_metrics
        }

    def _calculate_overall_health_score(self, component_health: Dict[str, Dict[str, Any]]) -> float:
        """全体ヘルススコア計算"""
        scores = []
        weights = {
            'error_handler': 0.3,
            'circuit_breaker': 0.2,
            'retry_system': 0.2,
            'fallback_system': 0.2,
            'metrics_collector': 0.1
        }
        
        weighted_sum = 0
        total_weight = 0
        
        for component, health in component_health.items():
            if 'score' in health:
                weight = weights.get(component, 0.1)
                weighted_sum += health['score'] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0

    def _determine_health_status(self, score: float) -> HealthStatus:
        """ヘルス状態判定"""
        if score >= 90:
            return HealthStatus.HEALTHY
        elif score >= 70:
            return HealthStatus.DEGRADED
        elif score >= 40:
            return HealthStatus.UNHEALTHY
        else:
            return HealthStatus.CRITICAL

    def _identify_active_issues(self, component_health: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """アクティブ問題特定"""
        issues = []
        
        for component, health in component_health.items():
            if health.get('status') in ['unhealthy', 'degraded']:
                issue = {
                    'component': component,
                    'status': health['status'],
                    'score': health.get('score', 0),
                    'description': f"{component} is {health['status']}",
                    'timestamp': time.time()
                }
                
                # 追加詳細情報
                if component == 'error_handler':
                    issue['details'] = {
                        'total_errors': health.get('total_errors', 0),
                        'resolution_rate': health.get('resolution_rate', 0)
                    }
                elif component == 'circuit_breaker':
                    issue['details'] = {
                        'unhealthy_circuits': health.get('unhealthy_circuits', 0),
                        'health_rate': health.get('health_rate', 0)
                    }
                
                issues.append(issue)
        
        return issues

    def _generate_recommendations(self, component_health: Dict[str, Dict[str, Any]], 
                                active_issues: List[Dict[str, Any]]) -> List[str]:
        """推奨事項生成"""
        recommendations = []
        
        for issue in active_issues:
            component = issue['component']
            
            if component == 'error_handler':
                if issue['details']['resolution_rate'] < 0.5:
                    recommendations.append("エラー自動回復機能の設定を見直してください")
                    recommendations.append("エラーパターンとリカバリーアクションを確認してください")
            
            elif component == 'circuit_breaker':
                if issue['details']['unhealthy_circuits'] > 0:
                    recommendations.append("サーキットブレーカーの閾値設定を調整してください")
                    recommendations.append("外部サービスの接続状況を確認してください")
            
            elif component == 'retry_system':
                recommendations.append("リトライポリシーの設定を見直してください")
                recommendations.append("リトライ対象の例外タイプを確認してください")
            
            elif component == 'fallback_system':
                recommendations.append("フォルバック戦略の有効性を確認してください")
                recommendations.append("フォルバック関数の実装を見直してください")
        
        # 全体的な推奨事項
        overall_score = self.current_health.overall_score if self.current_health else 0
        if overall_score < 70:
            recommendations.append("システム全体の負荷を確認してください")
            recommendations.append("リソース使用量の監視を強化してください")
        
        return list(set(recommendations))  # 重複除去

    def _check_custom_alerts(self):
        """カスタムアラートチェック"""
        for rule in self.custom_alert_rules.values():
            if not rule.enabled:
                continue
            
            try:
                self._evaluate_alert_rule(rule)
            except Exception as e:
                self.logger.error(f"アラートルール評価エラー: {rule.rule_id} - {str(e)}")

    def _evaluate_alert_rule(self, rule: AlertRule):
        """アラートルール評価"""
        # メトリクス取得
        metric_series = self.metrics_collector.get_metric_series(rule.metric_name)
        if not metric_series or not metric_series.points:
            return
        
        latest_point = metric_series.get_latest()
        current_value = latest_point.value
        
        # 条件評価
        if self._evaluate_condition(current_value, rule.condition):
            self._trigger_custom_alert(rule, current_value)

    def _evaluate_condition(self, value: float, condition: str) -> bool:
        """条件評価"""
        try:
            # 簡易条件パーサー
            condition = condition.strip()
            
            if condition.startswith('>'):
                threshold = float(condition[1:].strip())
                return value > threshold
            elif condition.startswith('<'):
                threshold = float(condition[1:].strip())
                return value < threshold
            elif condition.startswith('>='):
                threshold = float(condition[2:].strip())
                return value >= threshold
            elif condition.startswith('<='):
                threshold = float(condition[2:].strip())
                return value <= threshold
            elif condition.startswith('=='):
                threshold = float(condition[2:].strip())
                return abs(value - threshold) < 0.001
            elif condition.startswith('!='):
                threshold = float(condition[2:].strip())
                return abs(value - threshold) >= 0.001
            
            return False
            
        except Exception:
            return False

    def _trigger_custom_alert(self, rule: AlertRule, current_value: float):
        """カスタムアラート発動"""
        self.monitoring_stats['alerts_generated'] += 1
        
        alert_message = (
            f"カスタムアラート: {rule.name} - "
            f"{rule.metric_name} = {current_value} (条件: {rule.condition})"
        )
        
        self.logger.warning(alert_message)
        
        self.audit_logger.log_event(
            "custom_alert_triggered",
            alert_message,
            severity=rule.severity,
            rule_id=rule.rule_id,
            metric_name=rule.metric_name,
            current_value=current_value,
            condition=rule.condition
        )

    def _update_monitoring_stats(self):
        """監視統計更新"""
        # エラー数追跡
        error_stats = self.error_handler.get_error_statistics()
        self.monitoring_stats['errors_detected'] = error_stats['error_stats']['total_errors']
        
        # サーキットブレーカー統計
        circuit_summary = self.circuit_breaker_manager.get_health_summary()
        self.monitoring_stats['circuit_breaker_trips'] = circuit_summary['unhealthy_circuits']

    def _cleanup_old_metrics(self):
        """古いメトリクスクリーンアップ"""
        # メトリクス保持期間を超えた古いデータを削除
        # 実装は簡略化
        pass

    def get_system_health(self) -> Optional[SystemHealth]:
        """現在のシステムヘルス取得"""
        return self.current_health

    def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """ヘルス履歴取得"""
        cutoff_time = time.time() - (hours * 3600)
        return [
            health for health in self.health_history
            if health.last_updated >= cutoff_time
        ]

    def get_monitoring_summary(self) -> Dict[str, Any]:
        """監視概要取得"""
        return {
            'monitoring_mode': self.monitoring_mode.value,
            'is_monitoring': self.is_monitoring,
            'current_health': self.current_health.to_dict() if self.current_health else None,
            'monitoring_stats': self.monitoring_stats.copy(),
            'custom_alert_rules': len(self.custom_alert_rules),
            'enabled_alert_rules': len([r for r in self.custom_alert_rules.values() if r.enabled]),
            'health_check_interval': self.health_check_interval
        }

    def add_custom_alert_rule(self, rule: AlertRule):
        """カスタムアラートルール追加"""
        self.custom_alert_rules[rule.rule_id] = rule
        self.logger.info(f"カスタムアラートルール追加: {rule.name}")

    def remove_custom_alert_rule(self, rule_id: str) -> bool:
        """カスタムアラートルール削除"""
        if rule_id in self.custom_alert_rules:
            rule = self.custom_alert_rules.pop(rule_id)
            self.logger.info(f"カスタムアラートルール削除: {rule.name}")
            return True
        return False

    def enable_alert_rule(self, rule_id: str) -> bool:
        """アラートルール有効化"""
        if rule_id in self.custom_alert_rules:
            self.custom_alert_rules[rule_id].enabled = True
            return True
        return False

    def disable_alert_rule(self, rule_id: str) -> bool:
        """アラートルール無効化"""
        if rule_id in self.custom_alert_rules:
            self.custom_alert_rules[rule_id].enabled = False
            return True
        return False


# グローバル強化監視インスタンス
_global_enhanced_monitor: Optional[EnhancedMonitor] = None


def get_enhanced_monitor() -> EnhancedMonitor:
    """グローバル強化監視インスタンス取得"""
    global _global_enhanced_monitor
    if _global_enhanced_monitor is None:
        _global_enhanced_monitor = EnhancedMonitor()
    return _global_enhanced_monitor