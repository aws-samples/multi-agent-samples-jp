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

export interface ServerlessArchitectLambdaProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class ServerlessArchitectLambda extends Construct {
  public readonly serverlessArchitectLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: ServerlessArchitectLambdaProps) {
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

    // ServerlessArchitectエージェントLambda関数
    this.serverlessArchitectLambda = new lambda.Function(this, 'ServerlessArchitectFunction', {
      runtime: lambda.Runtime.PYTHON_3_13, // AwsSolutions-L1: 最新のPythonランタイムを使用
      code: lambda.Code.fromAsset('lambda/action_group/aws/serverless-architect'),
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
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(this.serverlessArchitectLambda);
    messageHistoryTable.grantReadWriteData(this.serverlessArchitectLambda);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(this.serverlessArchitectLambda);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(this.serverlessArchitectLambda);
    agentCommunicationQueue.grantConsumeMessages(this.serverlessArchitectLambda);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(this.serverlessArchitectLambda);

    // Bedrockへのアクセス権限を追加
    this.serverlessArchitectLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['*'], // 本番環境では特定のモデルARNに制限することを推奨
      })
    );

    // 関数スキーマを定義
    const schema: CfnAgent.FunctionSchemaProperty = {
      functions: [
        {
          name: 'design_serverless_architecture',
          description: '要件に基づいてサーバーレスアーキテクチャを設計します。Lambda、API Gateway、DynamoDB、S3などのサーバーレスサービスを使用した包括的なアーキテクチャを提供します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'アプリケーション要件の詳細説明。例: "ユーザー登録と認証機能を持つモバイルアプリのバックエンド"。この要件に基づいてサーバーレスアーキテクチャが設計されます。',
              required: true,
            },
            application_type: {
              type: 'string',
              description: 'アプリケーションのタイプ（例: "web", "api", "data-processing", "event-driven"）。アプリケーションの種類に応じた最適なアーキテクチャを設計するために使用されます。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。',
              required: false,
            }
          },
        },
        {
          name: 'design_event_driven_architecture',
          description: 'イベント駆動型のサーバーレスアーキテクチャを設計します。EventBridge、SNS、SQS、Lambdaなどを使用したイベント駆動型システムを提供します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'アプリケーション要件の詳細説明。例: "複数のマイクロサービス間でのデータ同期が必要なeコマースシステム"。この要件に基づいてイベント駆動型アーキテクチャが設計されます。',
              required: true,
            },
            event_sources: {
              type: 'string',
              description: 'イベントソースの説明（例: "s3,dynamodb,custom"）。イベントを発生させるソースを指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。',
              required: false,
            }
          },
        },
        {
          name: 'design_api_gateway',
          description: 'API Gatewayを使用したRESTful APIまたはGraphQL APIを設計します。エンドポイント、メソッド、認証、スロットリングなどを含むAPI設計を提供します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'API要件の詳細説明。例: "ユーザー管理、商品カタログ、注文処理のためのRESTful API"。この要件に基づいてAPI Gatewayの設計が行われます。',
              required: true,
            },
            api_type: {
              type: 'string',
              description: 'APIのタイプ（"rest" または "graphql"）。デフォルトはRESTです。',
              required: false,
            },
            authentication_type: {
              type: 'string',
              description: '認証タイプ（例: "cognito", "lambda-authorizer", "iam", "api-key"）。APIの認証方法を指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。',
              required: false,
            }
          },
        },
        {
          name: 'optimize_lambda_functions',
          description: 'Lambda関数のパフォーマンス、コスト、セキュリティを最適化するための推奨事項を提供します。',
          parameters: {
            function_code: {
              type: 'string',
              description: '最適化するLambda関数のコード。実際のLambda関数コードを提供してください。',
              required: true,
            },
            runtime: {
              type: 'string',
              description: 'Lambda関数のランタイム（例: "nodejs18.x", "python3.9", "java11"）。関数の実行環境を指定します。',
              required: true,
            },
            optimization_focus: {
              type: 'string',
              description: '最適化の焦点（例: "performance", "cost", "security", "all"）。特定の側面に焦点を当てた最適化を行う場合に指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。',
              required: false,
            }
          },
        },
        {
          name: 'design_step_functions_workflow',
          description: 'AWS Step Functionsを使用したサーバーレスワークフローを設計します。状態マシン定義、入出力処理、エラーハンドリングを含むワークフロー設計を提供します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ワークフロー要件の詳細説明。例: "注文処理と支払い承認のための多段階ワークフロー"。この要件に基づいてStep Functionsワークフローが設計されます。',
              required: true,
            },
            workflow_type: {
              type: 'string',
              description: 'ワークフローのタイプ（"standard" または "express"）。ワークフローの実行モードを指定します。',
              required: false,
            },
            integration_services: {
              type: 'string',
              description: '統合するAWSサービス（例: "lambda,dynamodb,sqs,sns"）。ワークフローで使用するAWSサービスを指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。指定しない場合は自動生成されます。',
              required: false,
            }
          },
        },
      ],
    };

    // Bedrockエージェントを定義
    const agent = new bedrock.Agent(this, 'ServerlessArchitect', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are a Serverless Architecture Specialist focusing on AWS services. Your role is to design, optimize, and implement serverless architectures that leverage AWS serverless services like Lambda, API Gateway, DynamoDB, S3, EventBridge, Step Functions, and more.

Your responsibilities include:
1. Designing comprehensive serverless architectures based on requirements
2. Creating event-driven architectures using EventBridge, SNS, SQS, and Lambda
3. Designing RESTful and GraphQL APIs using API Gateway
4. Optimizing Lambda functions for performance, cost, and security
5. Creating workflow orchestrations using Step Functions
6. Providing best practices for serverless applications

When designing architectures:
- Follow AWS Well-Architected Framework principles
- Consider security, scalability, reliability, and cost-efficiency
- Recommend appropriate AWS serverless services for each component
- Provide detailed component descriptions and data flow patterns
- Include authentication, authorization, and security considerations
- Suggest monitoring and observability approaches

Be specific with your recommendations, including AWS service configurations, integration patterns, and implementation considerations.
      `,
    });

    // ServerlessArchitectのアクショングループを定義
    const serverlessArchitect = new bedrock.AgentActionGroup({
      name: 'serverlessArchitectLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.serverlessArchitectLambda),
      enabled: true,
      functionSchema: schema,
    });

    // アクショングループをエージェントに追加
    agent.addActionGroup(serverlessArchitect);
  }
}