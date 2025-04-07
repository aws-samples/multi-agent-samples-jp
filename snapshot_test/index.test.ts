/**
 * CDKスナップショットテストのエントリーポイント
 * 
 * このファイルは、すべてのスタックのスナップショットテストを実行するためのエントリーポイントです。
 * 各スタックのテストファイルは個別に実行することもできますが、このファイルを使用することで
 * すべてのスナップショットテストを一度に実行できます。
 */

// 各スタックのスナップショットテストをインポート
import './bizdev-ma-agent-stack.test';
import './bizdev-ma-supervisor-stack.test';
import './bizdev-wf-stack.test';
import './cfnfa-ed-stack.test';
