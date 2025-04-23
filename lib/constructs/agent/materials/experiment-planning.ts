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

export interface ExperimentPlanningProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class ExperimentPlanning extends Construct {
  public readonly experimentPlanningAlias: bedrock.AgentAlias;  
  public readonly experimentPlanningLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: ExperimentPlanningProps) {
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
    const experimentPlanningRole = new iam.Role(this, 'ExperimentPlanningRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Experiment Planning Agent Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加
    experimentPlanningRole.addToPolicy(
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

    // 実験計画エージェントLambda関数
    this.experimentPlanningLambda = new lambda.Function(this, 'ExperimentPlanningFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/action_group/materials/experiment_planning'),
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
      role: experimentPlanningRole,
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(experimentPlanningRole);
    messageHistoryTable.grantReadWriteData(experimentPlanningRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(experimentPlanningRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(experimentPlanningRole);
    agentCommunicationQueue.grantConsumeMessages(experimentPlanningRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(experimentPlanningRole);

    // Bedrockへのアクセス権限を追加
    experimentPlanningRole.addToPolicy(
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
          name: 'create_experiment_plan',
          description: '提案された材料の検証実験計画を科学的根拠に基づいて詳細に作成します。材料の特性を効率的かつ正確に評価するための実験シーケンス、測定手法、サンプル準備方法を設計します。実験計画法（DOE）の原理を適用し、最小限の実験で最大の情報を得るための最適な実験設計を提案します。',
          parameters: {
            materials: {
              type: 'array',
              description: '検証対象の材料リスト。各材料の組成、構造、予測される特性、合成方法の推奨事項などを含みます。例: [{"composition": "CuInGaSe2", "structure": "chalcopyrite", "predicted_properties": {...}, "synthesis_recommendations": {...}}, ...]',
              required: true,
            },
            target_properties: {
              type: 'string',
              description: '検証すべき目標特性のセット（JSON文字列形式）。各特性の名前、目標値、許容範囲、単位、優先度、推奨される測定手法などを含みます。例: {"band_gap": {"value": 1.5, "unit": "eV", "range": [1.4, 1.6], "priority": "high", "measurement_methods": ["UV-Vis spectroscopy", "Photoluminescence"]}, ...}',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。指定しない場合は自動生成されます。複数の関連リクエスト間で状態を維持するために使用されます。',
              required: false,
            },
            available_equipment: {
              type: 'array',
              description: '利用可能な実験装置のリスト。各装置の名前、型番、測定可能な特性、精度、サンプル要件などを含みます。例: ["UV-Vis Spectrometer (Shimadzu UV-2600, 190-900nm, ±0.1nm)", "Hall Effect Measurement System (HMS-5000, 0.5-5T, RT-400K)", ...]',
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
          name: 'optimize_conditions',
          description: '特定の実験の条件（温度、圧力、時間、雰囲気、基板、前駆体濃度など）を科学的に最適化します。材料の特性、合成方法、測定技術に応じた最適なパラメータセットを決定し、実験の再現性、精度、効率を最大化します。統計的手法や材料科学の原理に基づいて、実験条件の最適範囲と予想される結果を提示します。',
          parameters: {
            experiment: {
              type: 'string',
              description: '最適化対象の実験。実験タイプ（合成、特性評価など）、対象材料、測定する特性、現在の条件設定などを含みます。例: {"type": "thin_film_deposition", "method": "sputtering", "material": "CuInGaSe2", "current_conditions": {"temperature": 550, "pressure": 5e-3, "power": 100, "time": 60}, ...}',
              required: true,
            },
            optimization_goal: {
              type: 'string',
              description: '最適化の目標。例: "収率最大化"、"純度最大化"、"結晶性向上"、"膜厚均一性向上"、"キャリア濃度最適化"、"測定精度向上"など。この目標に基づいて条件が最適化されます。',
              required: false,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の最適化結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。最適化の時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'estimate_resources',
          description: '実験計画に必要なリソース（時間、材料、装置、人員、コストなど）を詳細に見積もります。各実験ステップの所要時間、必要な材料の量と純度、装置の使用時間、専門技術者の関与度、消耗品、エネルギー消費などを含む包括的なリソース計画を提供します。これにより、実験の実現可能性評価や予算・スケジュール計画が可能になります。',
          parameters: {
            experiment_plan: {
              type: 'string',
              description: 'リソース見積もり対象の実験計画（JSON文字列形式）。実験ステップのシーケンス、各ステップの詳細（方法、条件、目的など）、使用する装置、対象材料などを含みます。例: {"steps": [{"name": "Substrate cleaning", "method": "ultrasonic bath", "duration": "30min", ...}, {"name": "Thin film deposition", ...}, ...], ...}',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の見積もり結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。見積もりの時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
      ],
    };

    const agent = new bedrock.Agent(this, 'ExperimentPlanningAgent',{
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
あなたは半導体材料科学の専門家で、特に実験計画と特性評価に特化しています。あなたの役割は、提案された半導体材料の特性を検証するための最適な実験計画を設計し、実験条件を最適化し、必要なリソースを見積もることです。

# 主な責務
1. **実験計画の作成**: 材料の特性を効率的かつ正確に評価するための包括的な実験計画を設計します。実験計画法（DOE）の原理を適用し、最小限の実験で最大の情報を得るための最適な実験設計を提案します。
2. **特性評価手法の選定**: 各目標特性（バンドギャップ、キャリア移動度、熱伝導率など）を測定するための最適な評価手法を選定し、測定プロトコルを詳細に記述します。
3. **実験条件の最適化**: 合成条件（温度、圧力、時間、雰囲気など）や測定条件（温度、光強度、電圧など）を最適化し、再現性と精度を最大化します。
4. **サンプル準備手順の設計**: 各評価手法に適したサンプルの準備方法（基板選択、サイズ、形状、表面処理など）を詳細に記述します。
5. **リソース見積もり**: 実験に必要な時間、材料、装置、人員、コストなどのリソースを詳細に見積もり、実験の実現可能性を評価します。
6. **データ解析手法の提案**: 実験データから材料特性を抽出するための適切なデータ解析手法を提案します。

# 専門知識
- 実験計画法（完全要因計画法、部分要因計画法、応答曲面法、タグチメソッドなど）
- 半導体特性評価技術（電気的・光学的・熱的・構造的特性の測定手法）
- 材料合成・加工技術（薄膜成長、バルク結晶成長、微細加工など）
- 分析機器（XRD、SEM、TEM、AFM、XPS、UV-Vis、ホール効果測定、DLTS、PL、ラマン分光など）
- 統計的データ解析（回帰分析、分散分析、主成分分析など）
- 実験室安全管理と品質管理

# 連携するエージェント
- **特性目標設定エージェント**: このエージェントから提供される目標特性セットに基づいて、適切な評価手法を選定します。特性の測定可能性や精度についてフィードバックを提供します。
- **材料逆設計エージェント**: このエージェントから提供される候補材料の情報に基づいて、適切な合成手法と評価手法を選定します。材料の特性や合成条件についての詳細情報を要求することがあります。

あなたの出力は、実際の実験実施の基盤となります。科学的に正確で、実現可能で、効率的な実験計画を提供することが重要です。常に最新の実験技術と評価手法に基づいて判断し、安全性と再現性を最優先してください。リソースの制約がある場合は、優先順位を明確にし、段階的なアプローチを提案してください。
      `,
    })

    const experimentPlanningActionGroup = new bedrock.AgentActionGroup({
      name: 'experimentPlanningLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.experimentPlanningLambda),
      enabled: true,
      functionSchema: schema
    });

    agent.addActionGroup(experimentPlanningActionGroup)

    // Alias定義
    this.experimentPlanningAlias = new bedrock.AgentAlias(this, 'ExperimentPlanningAlias', {
      agent: agent,
      description: 'Experiment Planning Agent for Materials Informatics'
    });
  }
}
