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

export interface CloudArchitectLambdaProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentStateTable: dynamodb.Table;
  messageHistoryTable: dynamodb.Table;
  artifactsBucket: s3.Bucket;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
}

export class CloudArchitectLambda extends Construct {
  public readonly cloudArchitectLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: CloudArchitectLambdaProps) {
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
    const cloudArchitectRole = new iam.Role(this, 'CloudArchitectRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Cloud Architect Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    cloudArchitectRole.addToPolicy(
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

    // クラウドアーキテクトLambda関数
    this.cloudArchitectLambda = new lambda.Function(this, 'CloudArchitectFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/action_group/aws/cloud-architect'),
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
      role: cloudArchitectRole, // カスタム実行ロールを使用
    });

    // DynamoDBへのアクセス権限を追加
    agentStateTable.grantReadWriteData(cloudArchitectRole);
    messageHistoryTable.grantReadWriteData(cloudArchitectRole);

    // S3へのアクセス権限を追加
    artifactsBucket.grantReadWrite(cloudArchitectRole);

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(cloudArchitectRole);
    agentCommunicationQueue.grantConsumeMessages(cloudArchitectRole);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(cloudArchitectRole);

    // Bedrockへのアクセス権限を追加
    cloudArchitectRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['arn:aws:bedrock:*:*:foundation-model/*'], 
        sid: 'BedrockInvokeModelAccess',
      })
    );

    // CloudFormationへのアクセス権限を追加
    cloudArchitectRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'cloudformation:DescribeStacks',
          'cloudformation:DescribeStackEvents',
          'cloudformation:DescribeStackResources',
          'cloudformation:GetTemplate'
        ],
        resources: [`arn:aws:cloudformation:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:stack/*`],
        sid: 'CloudFormationAccess',
      })
    );

    // 関数スキーマを定義
    const schema: CfnAgent.FunctionSchemaProperty = {
      functions: [
        {
          name: 'design_cloud_architecture',
          description: '要件に基づいてAWSクラウドアーキテクチャを設計します。コンポーネント、サービス選択、ネットワーク構成、セキュリティ設計などを含む包括的なクラウドアーキテクチャを提供します。',
          parameters: {
            requirement: {
              type: 'string',
              description: 'ユーザーから提供された要件の詳細説明。例: "高可用性のeコマースプラットフォームを構築したい"。この要件に基づいてクラウドアーキテクチャが設計されます。',
              required: true,
            },
            architecture_type: {
              type: 'string',
              description: 'アーキテクチャのタイプ（例: "serverless", "containerized", "microservices", "hybrid"）。特定のアーキテクチャパターンを指定する場合に使用します。',
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
          name: 'evaluate_architecture',
          description: 'AWS Well-Architected Frameworkに基づいて既存のクラウドアーキテクチャを評価し、改善点を提案します。運用上の優秀性、セキュリティ、信頼性、パフォーマンス効率、コスト最適化、持続可能性の観点から評価します。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '評価するアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、評価を行います。',
              required: true,
            },
            pillars: {
              type: 'string',
              description: '評価する特定のWell-Architected Frameworkの柱（例: "operational-excellence,security,reliability"）。指定しない場合はすべての柱で評価します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDは評価結果の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            }
          },
        },
        {
          name: 'create_infrastructure_diagram',
          description: 'クラウドアーキテクチャに基づいてMermaid形式のインフラストラクチャ図を作成します。AWSサービスとその接続を視覚的に表現します。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '以前に作成されたアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてインフラストラクチャ図を作成します。',
              required: true,
            },
            diagram_type: {
              type: 'string',
              description: '図の種類（例: "high-level", "detailed", "network", "security"）。作成するインフラストラクチャ図の詳細レベルや焦点を指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはインフラストラクチャ図の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            }
          },
        },
        {
          name: 'optimize_cost',
          description: '既存のクラウドアーキテクチャのコスト最適化分析を行い、コスト削減の機会を特定します。リザーブドインスタンス、Savings Plans、適切なサイジング、自動スケーリングなどの戦略を提案します。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '最適化するアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、コスト最適化分析を行います。',
              required: true,
            },
            monthly_budget: {
              type: 'string',
              description: '月間予算の上限（USD）。この予算内に収まるようなコスト最適化戦略を提案します。',
              required: false,
            },
            optimization_focus: {
              type: 'string',
              description: '最適化の焦点（例: "compute", "storage", "database", "network", "all"）。特定のリソースタイプに焦点を当てたコスト最適化を行う場合に指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはコスト最適化分析結果の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            }
          },
        },
        {
          name: 'design_disaster_recovery',
          description: 'クラウドアーキテクチャに基づいて災害復旧（DR）戦略を設計します。RPO/RTOの目標、バックアップ戦略、フェイルオーバーメカニズムを含む包括的なDR計画を提供します。',
          parameters: {
            architecture_id: {
              type: 'string',
              description: '災害復旧戦略を設計するアーキテクチャのID。このIDを使用して、S3から詳細なアーキテクチャ設計を取得し、それに基づいてDR戦略を設計します。',
              required: true,
            },
            rpo_hours: {
              type: 'string',
              description: '目標復旧時点（RPO）の時間数。データ損失を許容できる最大時間を指定します。',
              required: false,
            },
            rto_hours: {
              type: 'string',
              description: '目標復旧時間（RTO）の時間数。サービスダウンタイムを許容できる最大時間を指定します。',
              required: false,
            },
            project_id: {
              type: 'string',
              description: 'プロジェクトを識別するための一意のID。このIDはDR戦略の保存や、他のエージェントとの通信に使用されます。',
              required: true,
            }
          },
        },
      ],
    };

    // Bedrockエージェントを定義
    const agent = new bedrock.Agent(this, 'CloudArch', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are a Cloud Architect specializing in AWS cloud solutions. Your role is to design, evaluate, and optimize cloud architectures based on AWS best practices and the Well-Architected Framework.

Your responsibilities include:
1. Designing comprehensive cloud architectures based on requirements
2. Evaluating existing architectures against the AWS Well-Architected Framework
3. Creating infrastructure diagrams to visualize cloud solutions
4. Optimizing costs while maintaining performance, security, and reliability
5. Designing disaster recovery strategies to ensure business continuity
6. Providing recommendations for security, high availability, and scalability

When designing architectures:
- Follow AWS best practices and the Well-Architected Framework
- Consider security, reliability, performance efficiency, cost optimization, and operational excellence
- Recommend appropriate AWS services for each component
- Design for scalability, high availability, and fault tolerance
- Include network architecture, security controls, and monitoring solutions

Be specific with your recommendations, including AWS service names, configuration details, and implementation considerations.
      `,
    });

    // クラウドアーキテクトのアクショングループを定義
    const cloudArchitect = new bedrock.AgentActionGroup({
      name: 'cloudArchitectLambda',
      executor: bedrock.ActionGroupExecutor.fromlambdaFunction(this.cloudArchitectLambda),
      enabled: true,
      functionSchema: schema,
    });

    // アクショングループをエージェントに追加
    agent.addActionGroup(cloudArchitect);
  }
}
