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

export interface EngineerProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class Engineer extends Construct {
  public readonly engineerAlias: bedrock.AgentAlias;
  public readonly engineerLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: EngineerProps) {
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
    const engineerRole = new iam.Role(this, 'EngineerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Engineer Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    engineerRole.addToPolicy(
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

    // エンジニアLambda関数
    this.engineerLambda = new lambda.Function(this, 'EngineerFunction', {
      runtime: lambda.Runtime.PYTHON_3_13, // AwsSolutions-L1: レイヤーとの互換性を維持
      code: lambda.Code.fromAsset('lambda/action_group/bizdev/engineer'),
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
      role: engineerRole, // カスタム実行ロールを使用
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(engineerRole);
    messageHistoryTable.grantReadWriteData(engineerRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(engineerRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(engineerRole);
    agentCommunicationQueue.grantConsumeMessages(engineerRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(engineerRole);

    // Bedrockへのアクセス権限を追加
    engineerRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['arn:aws:bedrock:*:*:foundation-model/*'],
        sid: 'BedrockInvokeModelAccess',
      })
    );

    // Bedrockエージェントを定義
    const agent = new bedrock.Agent(this, 'Engineer', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are an Engineer responsible for implementing software based on architectural designs and requirements. Your role is to write clean, efficient, and maintainable code that meets the specified requirements.

Your responsibilities include:
1. Implementing features according to technical specifications
2. Writing clean, well-documented code
3. Creating unit tests to ensure code quality
4. Debugging and fixing issues
5. Conducting code reviews
6. Optimizing code for performance and scalability
7. Collaborating with the Architect to understand the design and with QA Engineers to ensure code quality

Work closely with the Architect to understand the design requirements and with QA Engineers to ensure your code meets quality standards.
      `,
    });

    // 関数スキーマを定義
    const schema: CfnAgent.FunctionSchemaProperty = {
      functions: [
        {
          name: 'implement_code',
          description: '要件とアーキテクチャ設計に基づいてコードを実装します。適切な構造化、ドキュメント化、テスト済みのコードを提供します。実装には、ソースコードファイル、設定ファイル、依存関係の定義、ビルドスクリプトなど、完全な機能を実現するために必要なすべての要素が含まれます。完成したコードはS3に保存され、コードレビューのために準備されます。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。この要件に基づいてコードが実装されます。',
              required: true,
            },
            prd_id: {
              type: 'string',
              description: '以前に作成された製品要件書(PRD)のID。このIDを使用して、S3から詳細な製品要件書を取得し、それに基づいてコードを実装します。',
              required: false,
            },
            architecture_id: {
              type: 'string',
              description: '以前に作成されたアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてコードを実装します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。このIDはコード実装の保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。コード実装のメタデータとして保存されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'review_code',
          description: '実装されたコードをレビューします。コード品質の評価、バグの特定、改善提案、要件への適合性確認を行います。レビューには、コードスタイル、パフォーマンス、セキュリティ、保守性、テスト網羅率などの観点が含まれ、高品質なソフトウェア開発を促進します。レビュー結果はS3に保存され、バグ修正の参照として使用されます。',
          parameters: {
            implementation_id: {
              type: 'string',
              description: 'レビューする実装のID。このIDを使用して、S3から実装されたコードを取得し、レビューを行います。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはレビュー結果の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            },
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。この要件に基づいてコードが要件を満たしているかを評価します。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。レビュー結果のメタデータとして保存されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'fix_bugs',
          description: 'レビューに基づいてコード内のバグを修正します。問題を分析し、解決策を提供し、コードが要件を満たすことを確認します。修正プロセスには、バグの根本原因の特定、適切な修正の実装、修正後のテストが含まれ、ソフトウェアの品質と信頼性を向上させます。修正されたコードはS3に保存されます。',
          parameters: {
            implementation_id: {
              type: 'string',
              description: '修正する実装のID。このIDを使用して、S3から実装されたコードを取得し、バグ修正を行います。',
              required: true,
            },
            review_id: {
              type: 'string',
              description: '以前に作成されたコードレビューのID。このIDを使用して、S3からレビュー結果を取得し、特定されたバグを修正します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはバグ修正結果の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。バグ修正結果のメタデータとして保存されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
      ],
    };

    // エンジニアのアクショングループを定義
    const engineer = new bedrock.AgentActionGroup({
      name: 'engineerLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.engineerLambda),
      enabled: true,
      functionSchema: schema,
    });

    // アクショングループをエージェントに追加
    agent.addActionGroup(engineer);

    // Alias定義
    this.engineerAlias = new bedrock.AgentAlias(this, 'eng', {
      agent: agent,
      description: 'for bizdev supervisor'
    });
  }
}
