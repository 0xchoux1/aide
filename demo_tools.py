#!/usr/bin/env python3
"""
AIDE ツールシステムのデモンストレーション
システム、ファイル、ネットワーク操作の基本機能を実演
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from tools.system_tool import SystemTool
from tools.file_tool import FileTool
from tools.network_tool import NetworkTool


def demo_system_tools():
    """システムツールのデモ"""
    print("=== システムツールデモ ===")
    
    # 安全モードでシステムツールを初期化
    system_tool = SystemTool(safe_mode=True)
    
    # 基本的なシステムコマンドを実行
    print("\n1. システム情報取得:")
    result = system_tool.get_system_info()
    print(f"ステータス: {result.status.value}")
    if result.metadata and 'system_info' in result.metadata:
        for key, value in result.metadata['system_info'].items():
            print(f"  {key}: {value}")
    
    # システムチェック実行
    print("\n2. システムヘルスチェック:")
    result = system_tool.run_system_check()
    print(f"ステータス: {result.status.value}")
    print(f"結果: {result.output}")
    
    # 安全なコマンド実行
    print("\n3. ディスク使用量チェック:")
    result = system_tool.execute("df -h")
    print(f"ステータス: {result.status.value}")
    if result.status.value == 'success':
        print("出力:")
        print(result.output)
    
    # 危険なコマンドのブロック確認
    print("\n4. 危険なコマンドのブロック確認:")
    result = system_tool.execute("rm -rf /")
    print(f"ステータス: {result.status.value}")
    print(f"エラー: {result.error}")
    
    print(f"\n実行統計: {system_tool.get_execution_stats()}")


def demo_file_tools():
    """ファイルツールのデモ"""
    print("\n=== ファイルツールデモ ===")
    
    file_tool = FileTool(safe_mode=True)
    
    # テスト用ファイルの作成
    test_content = """AIDE - Autonomous Infrastructure Development Expert
これはテストファイルです。
システム管理とファイル操作のテストに使用されます。
"""
    
    print("\n1. ファイル作成:")
    result = file_tool.write_file("/tmp/aide_test.txt", test_content)
    print(f"ステータス: {result.status.value}")
    print(f"結果: {result.output}")
    
    # ファイル読み取り
    print("\n2. ファイル読み取り:")
    result = file_tool.read_file("/tmp/aide_test.txt")
    print(f"ステータス: {result.status.value}")
    if result.status.value == 'success':
        print("ファイル内容:")
        print(result.output)
        print(f"メタデータ: {result.metadata}")
    
    # ファイル情報取得
    print("\n3. ファイル情報:")
    result = file_tool.get_file_info("/tmp/aide_test.txt")
    print(f"ステータス: {result.status.value}")
    if result.metadata and 'file_info' in result.metadata:
        info = result.metadata['file_info']
        print(f"  サイズ: {info['size']} bytes")
        print(f"  権限: {info['permissions']}")
        print(f"  タイプ: {info['type']}")
    
    # ディレクトリ一覧
    print("\n4. /tmpディレクトリ一覧:")
    result = file_tool.list_directory("/tmp")
    print(f"ステータス: {result.status.value}")
    if result.metadata:
        print(f"  総アイテム数: {result.metadata['total_items']}")
        print(f"  ファイル数: {result.metadata['files']}")
        print(f"  ディレクトリ数: {result.metadata['directories']}")
    
    # 保護されたパスへの書き込み試行
    print("\n5. 保護されたパスへの書き込み試行:")
    result = file_tool.write_file("/etc/test_file.txt", "test")
    print(f"ステータス: {result.status.value}")
    print(f"エラー: {result.error}")
    
    print(f"\n実行統計: {file_tool.get_execution_stats()}")


def demo_network_tools():
    """ネットワークツールのデモ"""
    print("\n=== ネットワークツールデモ ===")
    
    network_tool = NetworkTool(timeout=5)
    
    # DNS解決
    print("\n1. DNS解決テスト:")
    result = network_tool.dns_lookup("google.com")
    print(f"ステータス: {result.status.value}")
    if result.status.value == 'success':
        print("結果:")
        print(result.output)
    
    # ping テスト
    print("\n2. Ping テスト (Google DNS):")
    result = network_tool.ping("8.8.8.8", count=2)
    print(f"ステータス: {result.status.value}")
    if result.status.value == 'success':
        if result.metadata and 'stats' in result.metadata:
            stats = result.metadata['stats']
            print(f"  パケットロス: {stats.get('packet_loss', 'N/A')}%")
            print(f"  平均RTT: {stats.get('rtt_avg', 'N/A')}ms")
    
    # ポートスキャン（ローカルホスト）
    print("\n3. ローカルポートスキャン:")
    result = network_tool.port_scan("127.0.0.1", [22, 80, 443])
    print(f"ステータス: {result.status.value}")
    if result.metadata:
        print(f"  開いているポート: {result.metadata['open_ports']}")
        print(f"  閉じているポート: {result.metadata['closed_ports']}")
    
    # HTTP接続テスト
    print("\n4. HTTP接続テスト:")
    result = network_tool.test_http_connection("https://httpbin.org/get")
    print(f"ステータス: {result.status.value}")
    if result.metadata:
        print(f"  HTTPステータス: {result.metadata.get('http_code', 'N/A')}")
        print(f"  レスポンス時間: {result.metadata.get('total_time', 'N/A')}s")
    
    # ネットワーク接続性総合チェック
    print("\n5. ネットワーク接続性総合チェック:")
    result = network_tool.check_network_connectivity()
    print(f"ステータス: {result.status.value}")
    print("結果:")
    print(result.output)
    if result.metadata:
        print(f"  成功率: {result.metadata['success_rate']:.2%}")
    
    print(f"\n実行統計: {network_tool.get_execution_stats()}")


def demo_tool_integration():
    """ツール統合デモ"""
    print("\n=== ツール統合デモ ===")
    
    # 複数のツールを連携させたワークフロー例
    system_tool = SystemTool(safe_mode=True)
    file_tool = FileTool(safe_mode=True)
    network_tool = NetworkTool(timeout=3)
    
    print("\n統合ワークフロー: システム診断レポート生成")
    
    # 1. システム情報収集
    sys_info = system_tool.get_system_info()
    
    # 2. ネットワーク接続性チェック
    net_check = network_tool.check_network_connectivity()
    
    # 3. レポート作成
    report_lines = [
        "=== AIDE システム診断レポート ===",
        f"生成日時: {sys_info.timestamp}",
        "",
        "## システム情報",
    ]
    
    if sys_info.metadata and 'system_info' in sys_info.metadata:
        for key, value in sys_info.metadata['system_info'].items():
            report_lines.append(f"{key}: {value}")
    
    report_lines.extend([
        "",
        "## ネットワーク接続性",
        f"総合ステータス: {net_check.status.value}",
    ])
    
    if net_check.metadata:
        report_lines.append(f"成功率: {net_check.metadata['success_rate']:.2%}")
        report_lines.append(f"テスト数: {net_check.metadata['total_tests']}")
    
    report_content = "\n".join(report_lines)
    
    # 4. レポートファイル保存
    report_result = file_tool.write_file("/tmp/aide_diagnostic_report.txt", report_content)
    
    print(f"レポート生成: {report_result.status.value}")
    if report_result.status.value == 'success':
        print("診断レポートが /tmp/aide_diagnostic_report.txt に保存されました")
        
        # レポート内容を表示
        read_result = file_tool.read_file("/tmp/aide_diagnostic_report.txt")
        if read_result.status.value == 'success':
            print("\nレポート内容:")
            print(read_result.output)


def main():
    """メインデモ実行"""
    print("AIDE - Autonomous Infrastructure Development Expert")
    print("ツールシステムデモンストレーション")
    print("=" * 50)
    
    try:
        # 各ツールのデモを実行
        demo_system_tools()
        demo_file_tools()
        demo_network_tools()
        demo_tool_integration()
        
        print("\n" + "=" * 50)
        print("すべてのデモが完了しました！")
        print("AIDE ツールシステムは正常に動作しています。")
        
    except Exception as e:
        print(f"\nデモ実行中にエラーが発生しました: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())