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

export interface ProductManagerProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class ProductManager extends Construct {
  public readonly productManagerAlias: bedrock.AgentAlias;  
  public readonly productManagerLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: ProductManagerProps) {
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
    const productManagerRole = new iam.Role(this, 'ProductManagerRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Product Manager Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    productManagerRole.addToPolicy(
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

    // プロダクトマネージャーLambda関数
    this.productManagerLambda = new lambda.Function(this, 'ProductManagerFunction', {
      runtime: lambda.Runtime.PYTHON_3_13, // AwsSolutions-L1: レイヤーとの互換性を維持
      code: lambda.Code.fromAsset('lambda/action_group/bizdev/product-manager'),
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
      role: productManagerRole, // カスタム実行ロールを使用
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(productManagerRole);
    messageHistoryTable.grantReadWriteData(productManagerRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(productManagerRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(productManagerRole);
    agentCommunicationQueue.grantConsumeMessages(productManagerRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(productManagerRole);

    // Bedrockへのアクセス権限を追加
    productManagerRole.addToPolicy(
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
          name: 'analyze_requirement',
          description: 'ユーザーの要件を分析し、主要な機能、ターゲットユーザー、潜在的な課題を抽出します。この分析は、後続のプロダクト開発プロセスの基盤となり、ユーザーストーリーやPRDの作成に活用されます。分析結果はS3に保存され、プロジェクトの他のフェーズで参照できます。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。例: "モバイルアプリで家計簿を管理したい"。この要件に基づいて分析が行われます。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。このIDは分析結果の保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。分析結果のメタデータとして保存されます。',
              required: false,
            },
            timestamp: {
              type: 'string',
              description: '処理のタイムスタンプ。ISO 8601形式（例: 2023-01-01T12:00:00Z）で指定します。指定しない場合は現在時刻が使用されます。',
              required: false,
            }
          },
        },
        {
          name: 'create_user_stories',
          description: '要件に基づいてユーザーストーリーを作成します。各ストーリーは「〜として、〜したい、なぜなら〜」の形式で表現され、ユーザーの視点から機能の目的と価値を明確にします。これらのストーリーは開発チームが機能の優先順位付けや実装の方向性を決める際のガイドとなり、アーキテクトに自動的に通知されます。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。この要件に基づいてユーザーストーリーが作成されます。',
              required: true,
            },
            analysis_id: {
              type: 'string',
              description: '以前の要件分析のID。このIDを使用して、S3から詳細な分析結果を取得し、より適切なユーザーストーリーを作成します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはユーザーストーリーの保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。ユーザーストーリーのメタデータとして保存されます。',
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
          name: 'create_competitive_analysis',
          description: '要件に基づいて競合分析を行い、主要な競合他社、その強みと弱み、市場での位置づけを特定します。この分析は、製品の差別化ポイントを明確にし、市場での成功の可能性を高めるための戦略的な洞察を提供します。分析結果はS3に保存され、PRD作成時に参照されます。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。この要件に基づいて競合分析が行われます。',
              required: true,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDは競合分析結果の保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。競合分析結果のメタデータとして保存されます。',
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
          name: 'create_product_requirement_doc',
          description: 'ユーザーストーリーと競合分析に基づいて、製品要件書(PRD)を作成します。PRDには、概要、ユーザーストーリー、機能要件、非機能要件、タイムライン、成功指標などのセクションが含まれ、製品開発の包括的なガイドとなります。完成したPRDはアーキテクトとプロジェクトマネージャーに自動的に通知されます。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。この要件に基づいてPRDが作成されます。',
              required: true,
            },
            stories_id: {
              type: 'string',
              description: '以前に作成されたユーザーストーリーのID。このIDを使用して、S3からユーザーストーリーを取得し、PRDに組み込みます。',
              required: false,
            },
            competitive_analysis_id: {
              type: 'string',
              description: '以前に作成された競合分析のID。このIDを使用して、S3から競合分析を取得し、PRDに組み込みます。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはPRDの保存や、他のエージェントとの通信に使用されます。',
              required: false,
            },
            user_id: {
              type: 'string',
              description: 'リクエストを行ったユーザーのID。PRDのメタデータとして保存されます。',
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

    const agent = new bedrock.Agent(this, 'PdM',{
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are a Product Manager responsible for defining and managing software products. Your role is to understand user needs, define product requirements, and guide the development team to create successful products.

Your responsibilities include:
1. Analyzing user requirements and market needs
2. Creating user stories that clearly define features from a user's perspective
3. Conducting competitive analysis to understand the market landscape
4. Developing comprehensive Product Requirement Documents (PRDs)
5. Prioritizing features based on business value and user needs
6. Collaborating with stakeholders to gather feedback and refine requirements
7. Working with the development team to ensure the product meets requirements

Work closely with the Architect to translate requirements into technical specifications and with the Project Manager to ensure timely delivery of features.
      `,
    })

    const productManager = new bedrock.AgentActionGroup({
      name: 'productManagerLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.productManagerLambda),
      enabled: true,
      functionSchema: schema
    });

    agent.addActionGroup(productManager)

    // Alias定義
    this.productManagerAlias = new bedrock.AgentAlias(this, 'pdm', {
      agent: agent,
      description: 'for bizdev supervisor'
    });
  }
}
