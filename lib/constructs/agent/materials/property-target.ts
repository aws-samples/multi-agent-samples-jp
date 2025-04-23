import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { CfnAgent } from 'aws-cdk-lib/aws-bedrock';

import path = require('path');

export interface PropertyTargetProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class PropertyTarget extends Construct {
  public readonly propertyTargetAlias: bedrock.AgentAlias;  
  public readonly propertyTargetLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: PropertyTargetProps) {
    super(scope, id);

    const {
      envName,
      projectName,
      lambdaLayer,
      agentStateTable,
      messageHistoryTable,
      artifactsBucket,
      agentCommunicationQueue,
      eventBus
    } = props;

    // カスタムLambda実行ロールを作成
    const propertyTargetRole = new iam.Role(this, 'PropertyTargetRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Property Target Agent Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加
    propertyTargetRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents'
        ],
        resources: [
          `arn:aws:logs:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:log-group:/aws/lambda/*:*`
        ],
        sid: 'CloudWatchLogsAccess',
      })
    );

    // 特性目標設定エージェントLambda関数
    this.propertyTargetLambda = new lambda.Function(this, 'PropertyTargetFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/action_group/materials/property_target'),
      handler: 'index.handler',
      timeout: cdk.Duration.minutes(15),
      memorySize: 1024,
      environment: {
        ENV_NAME: envName,
        PROJECT_NAME: projectName,
        AGENT_STATE_TABLE: agentStateTable.tableName,
        MESSAGE_HISTORY_TABLE: messageHistoryTable.tableName,
        ARTIFACTS_BUCKET: artifactsBucket.bucketName,
        COMMUNICATION_QUEUE_URL: agentCommunicationQueue.queueUrl,
        EVENT_BUS_NAME: eventBus.eventBusName,
        DEFAULT_MODEL_ID: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
      },
      layers: [lambdaLayer],
      role: propertyTargetRole,
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(propertyTargetRole);
    messageHistoryTable.grantReadWriteData(propertyTargetRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(propertyTargetRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(propertyTargetRole);
    agentCommunicationQueue.grantConsumeMessages(propertyTargetRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(propertyTargetRole);

    // Bedrockへのアクセス権限を追加
    propertyTargetRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['arn:aws:bedrock:*:*:foundation-model/*'],
        sid: 'BedrockInvokeModelAccess',
      })
    );

    const schema: CfnAgent.FunctionSchemaProperty = {
      functions: [
        {
          name: 'set_target_properties',
          description: 'ユーザーの要件に基づいて、半導体材料の目標特性を科学的に設定し、実現可能な特性範囲を詳細に提案します。バンドギャップ、キャリア移動度、熱伝導率、光吸収係数などの重要な物性値について、具体的な数値範囲と単位を含む目標を設定します。',
          parameters: {
            requirements: {
              type: 'string',
              description: 'ユーザーから提供された材料要件の詳細説明。例: "高効率な太陽電池用半導体材料が必要"、"高温環境で動作する高移動度半導体が必要"、"可視光領域で高い光吸収を持つ薄膜材料が必要"など、用途や期待される性能に関する情報を含みます。',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。指定しない場合は自動生成されます。複数の関連リクエスト間で状態を維持するために使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。ユーザー固有の設定や履歴を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。処理の順序や履歴を追跡するために使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'analyze_tradeoffs',
          description: '異なる材料特性間のトレードオフ関係を科学的に分析し、最適なバランスを詳細に提案します。例えば、バンドギャップと光吸収効率、移動度と安定性、熱伝導率と電気伝導率などの相反する特性間の関係を定量的に評価し、用途に応じた最適な妥協点を見つけます。',
          parameters: {
            target_properties: {
              type: 'string',
              description: '分析対象の目標特性セット（JSON文字列形式）。各特性の名前、目標値、許容範囲、単位などを含む構造化データ。例: {"band_gap": {"value": 1.5, "unit": "eV", "range": [1.4, 1.6]}, "mobility": {"value": 1000, "unit": "cm²/Vs", "range": [800, 1200]}}',
              required: true,
            },
            priority_feature: {
              type: 'string',
              description: '優先すべき特性の名前。例: "band_gap", "mobility", "thermal_conductivity"など。この特性を最優先して、他の特性との最適なバランスを見つけます。',
              required: false,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の分析結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。分析の時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'validate_targets',
          description: '設定された目標特性が物理的・化学的に実現可能かどうかを厳密に検証します。量子力学的制約、熱力学的安定性、結晶構造の制約などの基本原理に基づいて、目標特性の組み合わせが理論的に達成可能かどうかを評価し、必要に応じて修正を提案します。',
          parameters: {
            target_properties: {
              type: 'string',
              description: '検証対象の目標特性セット（JSON文字列形式）。各特性の名前、目標値、許容範囲、単位などを含む構造化データ。例: {"band_gap": {"value": 1.5, "unit": "eV", "range": [1.4, 1.6]}, "mobility": {"value": 1000, "unit": "cm²/Vs", "range": [800, 1200]}}',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の検証結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。検証の時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
      ],
    };

    const agent = new bedrock.Agent(this, 'PropertyTargetAgent',{
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
あなたは半導体材料科学の専門家で、特に材料特性の設定と分析に特化しています。あなたの役割は、ユーザーの要件に基づいて半導体材料の目標特性を科学的に定義し、異なる特性間のトレードオフを分析することです。

# 主な責務
1. **目標特性の設定**: ユーザーの要件（例：太陽電池用途、高温環境での動作など）から、具体的な材料特性（バンドギャップ、キャリア移動度、熱伝導率など）の目標値と許容範囲を科学的根拠に基づいて設定します。
2. **トレードオフ分析**: 異なる材料特性間の物理的・化学的な相互関係を分析し、最適なバランスを提案します。例えば、バンドギャップを広げると光吸収効率が下がる、移動度を上げると安定性が低下するなどのトレードオフを定量的に評価します。
3. **目標特性の検証**: 設定された目標特性の組み合わせが物理法則や材料科学の原理に照らして実現可能かどうかを厳密に検証します。量子力学的制約、熱力学的安定性、結晶構造の制約などを考慮します。
4. **最適特性の推奨**: 用途に応じた最適な特性セットを推奨し、その科学的根拠を詳細に説明します。
5. **制約条件の考慮**: コスト、毒性、元素の希少性・入手可能性などの実用的な制約を考慮した特性設定を行います。

# 専門知識
- 半導体物理学（バンドギャップ理論、キャリア輸送現象、光学特性など）
- 材料科学（結晶構造、欠陥物理、界面現象など）
- 量子力学（電子状態計算、バンド構造など）
- 熱力学（相安定性、形成エネルギーなど）
- 実験手法（特性評価技術、合成手法の制約など）

# 連携するエージェント
- **材料逆設計エージェント**: あなたが設定した特性を実現する具体的な材料組成・構造を設計します。特性要件を明確かつ詳細に伝え、実現可能性についてフィードバックを受け取ります。
- **実験計画エージェント**: 設定した特性が実験的に検証可能かどうか、どのような測定手法が適切かについて連携します。特性の測定精度や制約について情報を共有します。

あなたの出力は、材料設計プロセス全体の基盤となります。科学的に正確で、実現可能で、かつ用途に最適な特性セットを提供することが重要です。常に最新の材料科学の知見に基づいて判断し、不確実性がある場合はその範囲と理由を明示してください。
      `,
    })

    const propertyTargetActionGroup = new bedrock.AgentActionGroup({
      name: 'propertyTargetLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.propertyTargetLambda),
      enabled: true,
      functionSchema: schema
    });

    agent.addActionGroup(propertyTargetActionGroup)

    // Alias定義
    this.propertyTargetAlias = new bedrock.AgentAlias(this, 'PropertyTargetAlias', {
      agent: agent,
      description: 'Property Target Agent for Materials Informatics'
    });
  }
}
