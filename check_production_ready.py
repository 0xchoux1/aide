#!/usr/bin/env python3
"""
AIDE 本番環境準備状況チェックスクリプト

このスクリプトは、AIDEが本番環境で正常に動作するために必要な
すべての依存関係と設定をチェックします。
"""

import sys
import os
import subprocess
import importlib.util

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ProductionReadinessChecker:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def check_python_version(self):
        """Pythonバージョンをチェック"""
        print("\n1. Python バージョンチェック:")
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major >= 3 and version.minor >= 8:
            self.successes.append(f"Python {version_str} ✅")
            print(f"   ✅ Python {version_str}")
        else:
            self.errors.append(f"Python 3.8+ が必要です (現在: {version_str})")
            print(f"   ❌ Python {version_str} - 3.8以上が必要です")
    
    def check_core_dependencies(self):
        """コア依存関係をチェック"""
        print("\n2. コア依存関係チェック:")
        
        core_deps = [
            ('chromadb', 'ベクターデータベース（RAGシステム）'),
            ('paramiko', 'SSH接続（リモート機能）'),
            ('psutil', 'システム監視・メトリクス収集'),
            ('requests', 'HTTP通信（通知機能）'),
            ('yaml', 'YAML設定ファイル処理')
        ]
        
        for module_name, description in core_deps:
            self._check_module(module_name, description)
    
    def check_ai_backend(self):
        """AIバックエンド（Claude Code）をチェック"""
        print("\n3. AI バックエンド（Claude Code）チェック:")
        
        # Claude Code CLIの存在確認
        claude_command = os.getenv('AIDE_CLAUDE_COMMAND', 'claude')
        try:
            result = subprocess.run([claude_command, '--version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.successes.append("Claude Code CLI インストール済み")
                print(f"   ✅ Claude Code CLI 利用可能")
                print(f"      コマンド: {claude_command}")
            else:
                self.errors.append("Claude Code CLI が見つかりません")
                print(f"   ❌ Claude Code CLI が見つかりません")
        except FileNotFoundError:
            self.errors.append(f"Claude Code CLI コマンド '{claude_command}' が見つかりません")
            print(f"   ❌ Claude Code CLI コマンド '{claude_command}' が見つかりません")
            print("      インストール方法: https://docs.anthropic.com/en/docs/claude-code")
    
    def check_environment_setup(self):
        """環境設定をチェック"""
        print("\n4. 環境設定チェック:")
        
        # .env ファイルの存在確認
        if os.path.exists('.env'):
            print("   ✅ .env ファイル存在")
            self.successes.append(".env ファイル設定済み")
        else:
            print("   ⚠️  .env ファイルが見つかりません")
            self.warnings.append(".env ファイルを作成してください: cp .env.example .env")
        
        # 重要な環境変数
        important_vars = [
            ('AIDE_ENV', 'production', '環境設定'),
            ('AIDE_DEBUG', 'false', 'デバッグモード'),
            ('AIDE_REMOTE_MOCK_MODE', 'false', 'リモート機能モックモード')
        ]
        
        for var_name, recommended, description in important_vars:
            value = os.getenv(var_name, 'not set')
            if value == 'not set':
                print(f"   ⚠️  {var_name}: 未設定 ({description})")
                self.warnings.append(f"{var_name} を設定してください（推奨: {recommended}）")
            elif value == recommended:
                print(f"   ✅ {var_name}: {value} ({description})")
            else:
                print(f"   ⚠️  {var_name}: {value} (推奨: {recommended}) ({description})")
                self.warnings.append(f"{var_name} は {recommended} に設定することを推奨")
    
    def check_configuration_files(self):
        """設定ファイルをチェック"""
        print("\n5. 設定ファイルチェック:")
        
        config_files = [
            ('config/servers.yaml', 'リモートサーバー設定'),
            ('config/defaults.py', 'デフォルト設定'),
            ('.env.example', '環境変数テンプレート')
        ]
        
        for file_path, description in config_files:
            if os.path.exists(file_path):
                print(f"   ✅ {file_path} ({description})")
                self.successes.append(f"{file_path} 存在")
            else:
                print(f"   ❌ {file_path} が見つかりません ({description})")
                self.errors.append(f"{file_path} が見つかりません")
    
    def check_data_directories(self):
        """データディレクトリをチェック"""
        print("\n6. データディレクトリチェック:")
        
        directories = [
            ('data', 'データルートディレクトリ'),
            ('logs', 'ログディレクトリ'),
            ('data/vectorstore', 'ベクターストアディレクトリ')
        ]
        
        for dir_path, description in directories:
            if os.path.exists(dir_path):
                if os.access(dir_path, os.W_OK):
                    print(f"   ✅ {dir_path} (書き込み可能) ({description})")
                else:
                    print(f"   ⚠️  {dir_path} (書き込み不可) ({description})")
                    self.warnings.append(f"{dir_path} に書き込み権限を付与してください")
            else:
                print(f"   ⚠️  {dir_path} が存在しません ({description})")
                self.warnings.append(f"mkdir -p {dir_path} でディレクトリを作成してください")
    
    def check_optional_dependencies(self):
        """オプション依存関係をチェック"""
        print("\n7. オプション依存関係チェック:")
        
        optional_deps = [
            ('redis', 'キャッシュ・セッション管理'),
            ('prometheus_client', 'メトリクス収集'),
            ('uvicorn', 'Webサーバー'),
            ('gunicorn', 'プロダクションWebサーバー')
        ]
        
        for module_name, description in optional_deps:
            if self._check_module_optional(module_name, description):
                print(f"   ✅ {module_name} ({description})")
            else:
                print(f"   ⚠️  {module_name} 未インストール ({description})")
    
    def check_system_resources(self):
        """システムリソースをチェック"""
        print("\n8. システムリソースチェック:")
        
        try:
            import psutil
            
            # メモリ
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            
            if total_gb >= 16:
                print(f"   ✅ メモリ: {total_gb:.1f}GB (推奨: 16GB以上)")
            elif total_gb >= 8:
                print(f"   ⚠️  メモリ: {total_gb:.1f}GB (推奨: 16GB以上)")
                self.warnings.append("メモリが推奨値（16GB）未満です")
            else:
                print(f"   ❌ メモリ: {total_gb:.1f}GB (最小: 8GB)")
                self.errors.append("メモリが最小要件（8GB）未満です")
            
            # ディスク空き容量
            disk = psutil.disk_usage('/')
            free_gb = disk.free / (1024**3)
            
            if free_gb >= 50:
                print(f"   ✅ ディスク空き容量: {free_gb:.1f}GB")
            elif free_gb >= 10:
                print(f"   ⚠️  ディスク空き容量: {free_gb:.1f}GB (推奨: 50GB以上)")
                self.warnings.append("ディスク空き容量が推奨値（50GB）未満です")
            else:
                print(f"   ❌ ディスク空き容量: {free_gb:.1f}GB (最小: 10GB)")
                self.errors.append("ディスク空き容量が最小要件（10GB）未満です")
                
        except ImportError:
            print("   ⚠️  psutil がインストールされていないため、リソースチェックをスキップ")
    
    def _check_module(self, module_name, description):
        """モジュールの存在をチェック"""
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            try:
                module = importlib.import_module(module_name)
                version = getattr(module, '__version__', 'unknown')
                print(f"   ✅ {module_name} v{version} ({description})")
                self.successes.append(f"{module_name} インストール済み")
                return True
            except Exception as e:
                print(f"   ❌ {module_name} インポートエラー: {e}")
                self.errors.append(f"{module_name} のインポートに失敗: {e}")
                return False
        else:
            print(f"   ❌ {module_name} 未インストール ({description})")
            self.errors.append(f"{module_name} がインストールされていません")
            return False
    
    def _check_module_optional(self, module_name, description):
        """オプションモジュールの存在をチェック（エラーにしない）"""
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    
    def generate_report(self):
        """チェック結果レポートを生成"""
        print("\n" + "="*60)
        print("本番環境準備状況レポート")
        print("="*60)
        
        total_checks = len(self.successes) + len(self.warnings) + len(self.errors)
        
        if self.errors:
            print(f"\n❌ エラー: {len(self.errors)}件")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")
        
        if self.warnings:
            print(f"\n⚠️  警告: {len(self.warnings)}件")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        if self.successes:
            print(f"\n✅ 成功: {len(self.successes)}件")
        
        print("\n" + "-"*60)
        
        if not self.errors:
            print("🎉 本番環境の準備が整っています！")
            print("\n次のステップ:")
            print("1. .env ファイルを本番環境用に設定")
            print("2. Claude Code CLI で認証: claude auth")
            print("3. python cli.py init で初期化")
            print("4. python cli.py status でシステム状態確認")
        else:
            print("❌ 本番環境の準備が完了していません")
            print("\n必要な対応:")
            print("1. pip install -r requirements.txt")
            print("2. 上記のエラーを解決")
            print("3. このスクリプトを再実行して確認")
    
    def run(self):
        """すべてのチェックを実行"""
        print("AIDE 本番環境準備状況チェック v1.0")
        print("="*60)
        
        self.check_python_version()
        self.check_core_dependencies()
        self.check_ai_backend()
        self.check_environment_setup()
        self.check_configuration_files()
        self.check_data_directories()
        self.check_optional_dependencies()
        self.check_system_resources()
        
        self.generate_report()

if __name__ == "__main__":
    checker = ProductionReadinessChecker()
    checker.run()