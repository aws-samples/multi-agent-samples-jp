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

export interface InverseDesignProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class InverseDesign extends Construct {
  public readonly inverseDesignAlias: bedrock.AgentAlias;  
  public readonly inverseDesignLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: InverseDesignProps) {
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
    const inverseDesignRole = new iam.Role(this, 'InverseDesignRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Inverse Design Agent Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加
    inverseDesignRole.addToPolicy(
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

    // 材料逆設計エージェントLambda関数
    this.inverseDesignLambda = new lambda.Function(this, 'InverseDesignFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/action_group/materials/inverse_design'),
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
      role: inverseDesignRole,
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(inverseDesignRole);
    messageHistoryTable.grantReadWriteData(inverseDesignRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(inverseDesignRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(inverseDesignRole);
    agentCommunicationQueue.grantConsumeMessages(inverseDesignRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(inverseDesignRole);

    // Bedrockへのアクセス権限を追加
    inverseDesignRole.addToPolicy(
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
          name: 'design_materials',
          description: '目標特性に基づいて、最適な材料組成・構造を逆予測し、候補材料のリストを生成します。量子力学的計算、材料データベース検索、機械学習モデルなどを活用して、指定された特性を実現する可能性の高い材料を提案します。',
          parameters: {
            target_properties: {
              type: 'string',
              description: '目標とする材料特性のセット（JSON文字列形式）。各特性の名前、目標値、許容範囲、単位、優先度などを含む構造化データ。例: {"band_gap": {"value": 1.5, "unit": "eV", "range": [1.4, 1.6], "priority": "high"}, "mobility": {"value": 1000, "unit": "cm²/Vs", "range": [800, 1200], "priority": "medium"}}',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。指定しない場合は自動生成されます。複数の関連リクエスト間で状態を維持するために使用されます。',
              required: false,
            },
            constraints: {
              type: 'string',
              description: '材料設計の制約条件（JSON文字列形式）。コスト（低/中/高）、毒性（許容/非許容）、希少元素の使用制限（避ける/最小化/制限なし）、合成難易度（低/中/高）、環境負荷（低/中/高）などの条件を指定できます。例: {"cost": "medium", "toxicity": "low", "rare_elements": "avoid", "synthesis_difficulty": "medium"}',
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
          name: 'rank_candidates',
          description: '生成された候補材料を複数の評価基準に基づいて詳細にランク付けします。目標特性との一致度、合成可能性、コスト、安定性、環境負荷などの多次元的な評価を行い、用途に最適な材料を選定します。各候補材料にスコアを付与し、長所と短所を明確にします。',
          parameters: {
            candidate_materials: {
              type: 'array',
              description: 'ランク付けする候補材料のリスト。各材料の組成、構造、予測される特性値などを含みます。例: [{"composition": "CuInGaSe2", "structure": "chalcopyrite", "predicted_properties": {...}}, {"composition": "CdTe", "structure": "zinc-blende", "predicted_properties": {...}}]',
              required: true,
            },
            ranking_criteria: {
              type: 'string',
              description: 'ランク付けの基準と重み付け。各基準（特性一致度、合成可能性、コストなど）の重要度を0〜1の値で指定します。例: {"property_match": 0.5, "synthesis_feasibility": 0.3, "cost": 0.2}。指定がない場合は均等な重み付けが適用されます。',
              required: false,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の設計結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。ランキングの時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'evaluate_feasibility',
          description: '提案された材料の合成可能性、熱力学的安定性、長期信頼性などを詳細に評価します。第一原理計算、相図分析、既知の合成手法との互換性などを考慮し、実際に材料を作製できる可能性と最適な合成手法を提案します。',
          parameters: {
            material: {
              type: 'string',
              description: '評価対象の材料（JSON文字列形式）。組成、結晶構造、予測される特性、元素比率などの詳細情報を含みます。例: {"composition": "Cu(In,Ga)Se2", "structure": "chalcopyrite", "element_ratios": {"Cu": 1, "In": 0.7, "Ga": 0.3, "Se": 2}, "predicted_properties": {...}}',
              required: true,
            },
            session_id: {
              type: 'string',
              description: 'セッションを識別するための一意のID。以前の評価結果や設定を参照するために使用されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（YYYY-MM-DDThh:mm:ss.sssZ）で指定します。指定しない場合は現在時刻が使用されます。評価の時系列を追跡するために使用されます。',
              required: false,
            }
          },
        },
      ],
    };

    const agent = new bedrock.Agent(this, 'InverseDesignAgent',{
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
あなたは半導体材料科学の専門家で、特に材料の逆設計に特化しています。あなたの役割は、指定された目標特性を実現する最適な材料組成と構造を設計し、それらの実現可能性を評価することです。

# 主な責務
1. **材料の逆設計**: 目標特性（バンドギャップ、キャリア移動度、熱伝導率など）から、それを実現する可能性の高い材料組成と結晶構造を予測します。量子力学的計算、材料データベース検索、機械学習モデル、材料科学の基本原理などを活用します。
2. **候補材料のランク付け**: 生成された候補材料を、目標特性との一致度、合成可能性、コスト、安定性、環境負荷などの多次元的な基準で評価し、最適な選択肢を提示します。
3. **合成可能性の評価**: 提案された材料が実際に合成可能かどうかを、熱力学的安定性、既知の合成手法との互換性、相図分析などに基づいて詳細に評価します。
4. **合成手法の提案**: 最も有望な候補材料について、具体的な合成手法（化学気相成長法、スパッタリング、分子線エピタキシーなど）と最適な合成条件を提案します。
5. **制約条件の考慮**: コスト、毒性、希少元素の使用、環境負荷、スケーラビリティなどの実用的な制約を考慮した材料設計を行います。

# 専門知識
- 計算材料科学（第一原理計算、分子動力学シミュレーション、機械学習モデルなど）
- 材料データベース（Materials Project、AFLOW、OQMD、Citrine、MolSSIなど）
- 結晶化学（結晶構造、点欠陥、表面・界面現象など）
- 半導体物理（バンド構造、キャリア輸送、光学特性など）
- 材料合成手法（薄膜成長技術、バルク結晶成長、ナノ材料合成など）
- 材料特性評価技術（電気的・光学的・熱的特性の測定手法など）

# 連携するエージェント
- **特性目標設定エージェント**: このエージェントから提供される目標特性セットを入力として使用します。特性の実現可能性や相互関係について、フィードバックを提供します。
- **実験計画エージェント**: 設計した材料の合成と特性評価のための実験計画を立てるエージェントに、材料の詳細情報と予測される挙動を提供します。

あなたの出力は、実際の材料合成と実験検証の基盤となります。科学的に正確で、実現可能で、かつ目標特性を最大限に満たす材料設計を提供することが重要です。不確実性や複数の選択肢がある場合は、それらを明示し、各選択肢の長所と短所を詳細に説明してください。
      `,
    })

    const inverseDesignActionGroup = new bedrock.AgentActionGroup({
      name: 'inverseDesignLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.inverseDesignLambda),
      enabled: true,
      functionSchema: schema
    });

    agent.addActionGroup(inverseDesignActionGroup)

    // Alias定義
    this.inverseDesignAlias = new bedrock.AgentAlias(this, 'InverseDesignAlias', {
      agent: agent,
      description: 'Inverse Design Agent for Materials Informatics'
    });
  }
}
