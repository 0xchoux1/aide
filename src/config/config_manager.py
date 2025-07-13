"""
AIDE 設定管理システム

設定の読み込み、保存、検証、マージを管理
"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List, Union, Type
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
from copy import deepcopy

from .defaults import (
    DEFAULT_CONFIG,
    ConfigProfile
)


class ConfigError(Exception):
    """設定関連エラー"""
    pass


class ValidationError(ConfigError):
    """設定検証エラー"""
    pass


@dataclass
class ConfigKey:
    """設定キー情報"""
    key: str
    description: str
    default_value: Any
    required: bool = False
    validation_rule: Optional[Dict[str, Any]] = None


class ConfigFormat(Enum):
    """設定ファイル形式"""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"


class ConfigValidator:
    """設定値検証クラス"""
    
    def __init__(self, validation_rules: Dict[str, Dict] = None):
        self.validation_rules = validation_rules or {}
        self.logger = logging.getLogger(__name__)
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        設定全体を検証
        
        Args:
            config: 検証する設定辞書
            
        Returns:
            エラーメッセージのリスト（空の場合は検証成功）
        """
        errors = []
        
        try:
            self._validate_recursive(config, "", errors)
        except Exception as e:
            errors.append(f"検証中にエラーが発生: {str(e)}")
        
        return errors
    
    def _validate_recursive(self, config: Dict[str, Any], path_prefix: str, errors: List[str]):
        """再帰的に設定を検証"""
        for key, value in config.items():
            current_path = f"{path_prefix}.{key}" if path_prefix else key
            
            if isinstance(value, dict):
                self._validate_recursive(value, current_path, errors)
            else:
                self._validate_single_value(current_path, value, errors)
    
    def _validate_single_value(self, key_path: str, value: Any, errors: List[str]):
        """単一の設定値を検証"""
        if key_path not in self.validation_rules:
            return
        
        rule = self.validation_rules[key_path]
        
        # 型チェック
        expected_type = rule.get("type")
        if expected_type:
            if isinstance(expected_type, list):
                if not any(isinstance(value, t) for t in expected_type):
                    errors.append(f"{key_path}: 無効な型 {type(value).__name__}, 期待値: {expected_type}")
                    return
            elif not isinstance(value, expected_type):
                errors.append(f"{key_path}: 無効な型 {type(value).__name__}, 期待値: {expected_type.__name__}")
                return
        
        # 範囲チェック
        if "min" in rule and value < rule["min"]:
            errors.append(f"{key_path}: 値 {value} が最小値 {rule['min']} 未満")
        
        if "max" in rule and value > rule["max"]:
            errors.append(f"{key_path}: 値 {value} が最大値 {rule['max']} 超過")
        
        # 選択肢チェック
        if "choices" in rule and value not in rule["choices"]:
            errors.append(f"{key_path}: 無効な選択肢 {value}, 有効値: {rule['choices']}")
        
        # カスタム検証
        if "validator" in rule:
            validator_func = rule["validator"]
            if not validator_func(value):
                errors.append(f"{key_path}: カスタム検証に失敗")
    
    def validate_key(self, key_path: str, value: Any) -> bool:
        """単一キーの検証"""
        errors = []
        self._validate_single_value(key_path, value, errors)
        return len(errors) == 0


class ConfigLoader:
    """設定ファイル読み込みクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def load_from_file(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        ファイルから設定を読み込み
        
        Args:
            file_path: 設定ファイルパス
            
        Returns:
            設定辞書
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ConfigError(f"設定ファイルが見つかりません: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if file_path.suffix.lower() in ['.yml', '.yaml']:
                    return yaml.safe_load(f) or {}
                elif file_path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    raise ConfigError(f"サポートされていない設定ファイル形式: {file_path.suffix}")
        
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            raise ConfigError(f"設定ファイル解析エラー {file_path}: {str(e)}")
        except Exception as e:
            raise ConfigError(f"設定ファイル読み込みエラー {file_path}: {str(e)}")
    
    def load_from_env(self, prefix: str = "AIDE_") -> Dict[str, Any]:
        """
        環境変数から設定を読み込み
        
        Args:
            prefix: 環境変数のプレフィックス
            
        Returns:
            設定辞書
        """
        config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # AIDE_SYSTEM_DEBUG_MODE -> system.debug_mode
                config_key = key[len(prefix):].lower().replace('_', '.')
                
                # 型変換試行
                parsed_value = self._parse_env_value(value)
                self._set_nested_value(config, config_key, parsed_value)
        
        return config
    
    def _parse_env_value(self, value: str) -> Any:
        """環境変数値を適切な型に変換"""
        # ブール値
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 数値
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # JSON配列/オブジェクト
        if value.startswith(('[', '{')):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # 文字列
        return value
    
    def _set_nested_value(self, config: Dict[str, Any], key_path: str, value: Any):
        """ネストした辞書に値を設定"""
        keys = key_path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value


class ConfigManager:
    """メイン設定管理クラス"""
    
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.config_dir = self.project_root / "config"
        self.logger = logging.getLogger(__name__)
        
        self.validator = ConfigValidator()
        self.loader = ConfigLoader()
        
        self._config: Dict[str, Any] = {}
        self._profile: ConfigProfile = ConfigProfile.DEVELOPMENT
        self._config_files: List[Path] = []
        
        # 初期化
        self._initialize()
    
    def _initialize(self):
        """設定マネージャーを初期化"""
        try:
            # デフォルト設定をロード
            self._config = deepcopy(DEFAULT_CONFIG)
            
            # 環境変数から設定を読み込み
            env_config = self.loader.load_from_env()
            if env_config:
                self._merge_config(env_config)
            
            # プロファイル設定
            profile_name = os.environ.get('AIDE_PROFILE', 'development')
            try:
                self._profile = ConfigProfile(profile_name)
            except ValueError:
                self.logger.warning(f"無効なプロファイル {profile_name}, developmentを使用")
                self._profile = ConfigProfile.DEVELOPMENT
            
            # プロファイル固有設定をマージ
            from .defaults import ENVIRONMENT_DEFAULTS
            if self._profile.value in ENVIRONMENT_DEFAULTS:
                profile_config = ENVIRONMENT_DEFAULTS[self._profile.value]
                self._merge_config(profile_config)
            
            # 設定ファイルをロード
            self._load_config_files()
            
            # 設定を検証
            self._validate_current_config()
            
        except Exception as e:
            self.logger.error(f"設定初期化エラー: {str(e)}")
            raise ConfigError(f"設定初期化に失敗: {str(e)}")
    
    def _load_config_files(self):
        """設定ファイルを読み込み"""
        config_files = [
            self.config_dir / "aide.yaml",
            self.config_dir / "aide.yml", 
            self.config_dir / "aide.json",
            self.project_root / "aide.yaml",
            self.project_root / "aide.yml",
            self.project_root / "aide.json"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                try:
                    file_config = self.loader.load_from_file(config_file)
                    self._merge_config(file_config)
                    self._config_files.append(config_file)
                    self.logger.info(f"設定ファイルをロード: {config_file}")
                except ConfigError as e:
                    self.logger.error(f"設定ファイル読み込みエラー {config_file}: {str(e)}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """設定をマージ"""
        self._deep_merge(self._config, new_config)
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        """辞書を深くマージ"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _validate_current_config(self):
        """現在の設定を検証"""
        errors = self.validator.validate_config(self._config)
        if errors:
            error_msg = "設定検証エラー:\n" + "\n".join(f"  - {error}" for error in errors)
            self.logger.error(error_msg)
            raise ValidationError(error_msg)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        設定値を取得
        
        Args:
            key_path: ドット記法のキーパス (例: "system.debug_mode")
            default: デフォルト値
            
        Returns:
            設定値
        """
        keys = key_path.split('.')
        current = self._config
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any, validate: bool = True) -> bool:
        """
        設定値を設定
        
        Args:
            key_path: ドット記法のキーパス
            value: 設定値
            validate: 検証を実行するか
            
        Returns:
            設定成功フラグ
        """
        if validate and not self.validator.validate_key(key_path, value):
            self.logger.error(f"設定検証失敗: {key_path} = {value}")
            return False
        
        keys = key_path.split('.')
        current = self._config
        
        # ネストした辞書を作成
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        return True
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """設定セクション全体を取得"""
        return self.get(section, {})
    
    def get_profile(self) -> ConfigProfile:
        """現在のプロファイルを取得"""
        return self._profile
    
    def switch_profile(self, profile: ConfigProfile):
        """プロファイルを切り替え"""
        self._profile = profile
        self._initialize()  # 再初期化
    
    def set_profile(self, profile_name: str):
        """プロファイルを文字列で設定"""
        try:
            profile = ConfigProfile(profile_name)
            self.switch_profile(profile)
        except ValueError:
            raise ConfigError(f"無効なプロファイル: {profile_name}")
    
    def save_to_file(self, file_path: Union[str, Path], format: ConfigFormat = ConfigFormat.YAML):
        """
        設定をファイルに保存
        
        Args:
            file_path: 保存先ファイルパス
            format: ファイル形式
        """
        file_path = Path(file_path)
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                if format == ConfigFormat.YAML:
                    yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                elif format == ConfigFormat.JSON:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                else:
                    raise ConfigError(f"サポートされていない形式: {format}")
            
            self.logger.info(f"設定を保存: {file_path}")
            
        except Exception as e:
            raise ConfigError(f"設定保存エラー {file_path}: {str(e)}")
    
    def reload(self):
        """設定を再読み込み"""
        self._initialize()
    
    def export_config(self) -> Dict[str, Any]:
        """現在の設定をエクスポート"""
        return deepcopy(self._config)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """設定サマリーを取得"""
        return {
            "profile": self._profile.value,
            "config_files": [str(f) for f in self._config_files],
            "system_info": {
                "version": self.get("system.version"),
                "environment": self.get("system.environment"),
                "debug_mode": self.get("system.debug_mode"),
                "log_level": self.get("system.log_level")
            },
            "enabled_features": {
                "claude_integration": self.get("claude_integration.enabled"),
                "rag_system": self.get("rag_system.enabled"),
                "auto_implementation": self.get("features.auto_implementation", True),
                "ai_enhanced_analysis": self.get("features.ai_enhanced_analysis", True)
            }
        }
    
    def validate_config(self) -> List[str]:
        """現在の設定を検証"""
        return self.validator.validate_config(self._config)


# グローバル設定マネージャーインスタンス
_global_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """グローバル設定マネージャーを取得"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigManager()
    return _global_config_manager


def get_config(key_path: str, default: Any = None) -> Any:
    """設定値を取得（便利関数）"""
    return get_config_manager().get(key_path, default)


def set_config(key_path: str, value: Any) -> bool:
    """設定値を設定（便利関数）"""
    return get_config_manager().set(key_path, value)