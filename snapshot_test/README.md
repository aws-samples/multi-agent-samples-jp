# CDK スナップショットテスト

このディレクトリには、CDKスタックのスナップショットテストが含まれています。スナップショットテストは、インフラストラクチャコードの変更が意図したとおりであることを確認するための効果的な方法です。

## テスト対象のスタック

- `bizdev-ma-agent-stack.test.ts` - Business Development Multi-Agent スタックのテスト
- `bizdev-ma-supervisor-stack.test.ts` - Business Development Supervisor スタックのテスト
- `bizdev-wf-stack.test.ts` - Business Development Workflow スタックのテスト
- `cfnfa-ed-stack.test.ts` - CloudFormation Analysis Event-Driven スタックのテスト

## テストの実行方法

### すべてのスナップショットテストを実行

```bash
npm test -- snapshot_test
```

### 特定のスタックのスナップショットテストを実行

```bash
npm test -- snapshot_test/bizdev-ma-agent-stack.test.ts
```

### スナップショットの更新

インフラストラクチャに意図的な変更を加えた場合は、スナップショットを更新する必要があります。

```bash
npm test -- -u snapshot_test
```

## スナップショットテストの仕組み

1. テストでは、各CDKスタックをインスタンス化します
2. スタックからCloudFormationテンプレートを生成します
3. 生成されたテンプレートをスナップショットと比較します
4. 差異がある場合、テストは失敗します

## スナップショットテストのベストプラクティス

1. **決定論的なテスト**: CDKは一部のリソース名にランダムな文字列を含めることがあります。これらをテスト時に固定値に置き換えることを検討してください。
2. **環境変数の管理**: テスト中に必要な環境変数を適切に設定してください。
3. **スナップショットの更新**: 意図的な変更がある場合のみスナップショットを更新してください。
4. **レビュープロセス**: スナップショットの変更をコードレビューの一部として確認してください。
