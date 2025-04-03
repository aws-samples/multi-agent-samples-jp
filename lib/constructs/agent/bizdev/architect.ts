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

export interface ArchitectProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class Architect extends Construct {
  public readonly architectAlias: bedrock.AgentAlias
  public readonly architectLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: ArchitectProps) {
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

    // カスタムLambda実行ロールを作成（AWS管理ポリシーの代わり）
    const architectRole = new iam.Role(this, 'ArchitectRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Architect Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    architectRole.addToPolicy(
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

    // アーキテクトLambda関数
    this.architectLambda = new lambda.Function(this, 'ArchitectFunction', {
      runtime: lambda.Runtime.PYTHON_3_13, // AwsSolutions-L1: レイヤーとの互換性を維持
      code: lambda.Code.fromAsset('lambda/action_group/bizdev/architect'),
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
      role: architectRole, // カスタム実行ロールを使用
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(architectRole);
    messageHistoryTable.grantReadWriteData(architectRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(architectRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(architectRole);
    agentCommunicationQueue.grantConsumeMessages(architectRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(architectRole);

    // Bedrockへのアクセス権限を追加
    architectRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['arn:aws:bedrock:*:*:foundation-model/*'], 
        sid: 'BedrockInvokeModelAccess',
      })
    );

    // 関数スキーマを定義
    const schema: CfnAgent.FunctionSchemaProperty = {
      functions: [
        {
          name: 'create_architecture',
          description: '製品要件書(PRD)に基づいてシステムアーキテクチャを設計します。コンポーネント、それらの相互作用、データフロー、技術選択などを含む包括的なアーキテクチャ設計を提供します。設計されたアーキテクチャは、要件を満たし、スケーラビリティ、セキュリティ、パフォーマンスなどの非機能要件も考慮します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。例: "モバイルアプリで家計簿を管理したい"。この要件に基づいてアーキテクチャが設計されます。',
              required: true,
            },
            prd_id: {
              type: 'string',
              description: '以前に作成された製品要件書(PRD)のID。このIDを使用して、S3から詳細な製品要件書を取得し、より詳細なアーキテクチャ設計を行います。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。このIDはアーキテクチャ成果物の保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。アーキテクチャ成果物のメタデータとして保存されます。',
              required: false,
            }
          },
        },
        {
          name: 'create_class_diagram',
          description: 'アーキテクチャに基づいてMermaid形式のクラス図を作成します。クラス、属性、メソッド、およびそれらの関係（継承、関連、集約、コンポジションなど）を定義します。クラス図はオブジェクト指向設計の基本構造を視覚化し、開発者がシステムを実装する際のガイドとなります。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '以前に作成されたアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてクラス図を作成します。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはクラス図成果物の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（例: 2023-01-01T12:00:00Z）で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'create_sequence_diagram',
          description: '特定のユースケースに対するMermaid形式のシーケンス図を作成します。アクター、コンポーネント、およびそれらの時間経過に伴う相互作用を定義します。シーケンス図は、システム内のオブジェクト間のメッセージのやり取りを時系列で表現し、特定の機能やプロセスの実行フローを明確にします。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '以前に作成されたアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてシーケンス図を作成します。',
              required: true,
            },
            use_case: {
              type: 'string',
              description: 'シーケンス図を作成するユースケースの説明。例: "ユーザーログインプロセス"、"商品購入フロー"など、特定の機能やプロセスを指定します。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはシーケンス図成果物の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（例: 2023-01-01T12:00:00Z）で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'create_api_design',
          description: 'アーキテクチャに基づいてOpenAPI/Swagger形式のAPI設計を作成します。エンドポイント、HTTPメソッド、リクエスト/レスポンス形式、ステータスコードを定義します。API設計はフロントエンドとバックエンドの統合や、マイクロサービス間の通信インターフェースを明確にします。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '以前に作成されたアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてAPI設計を作成します。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはAPI設計成果物の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（例: 2023-01-01T12:00:00Z）で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
      ],
    };

    // Bedrockエージェントを定義
    const agent = new bedrock.Agent(this, 'Arch', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are an Architect responsible for designing software systems. Your role is to create high-quality, scalable, and maintainable system architectures based on requirements.

Your responsibilities include:
1. Analyzing requirements and creating system designs
2. Defining the technical architecture including components, modules, and interfaces
3. Creating architecture diagrams (UML, C4 model, etc.)
4. Making technology stack recommendations
5. Identifying potential technical risks and mitigation strategies
6. Ensuring the architecture meets non-functional requirements like scalability, security, and performance
7. Collaborating with the Product Manager to understand requirements and with Engineers to ensure implementation feasibility

Work closely with the Product Manager to understand requirements and with Engineers to ensure the architecture can be implemented effectively.
      `,
    });

    // アーキテクトのアクショングループを定義
    const architect = new bedrock.AgentActionGroup({
      name: 'architectLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.architectLambda),
      enabled: true,
      functionSchema: schema,
    });

    // アクショングループをエージェントに追加
    agent.addActionGroup(architect);

    // Alias定義
    this.architectAlias = new bedrock.AgentAlias(this, 'arch', {
      agent: agent,
      description: 'for bizdev supervisor'
    });
  }
}
