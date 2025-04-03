import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as events from 'aws-cdk-lib/aws-events';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

// 各コンストラクトのインポート
import { ProductManager } from './constructs/agent/bizdev/product-manager';
import { Architect } from './constructs/agent/bizdev/architect';
import { Engineer } from './constructs/agent/bizdev/engineer';
// import { ApiLambda } from './constructs/infrastructure/api-lambda';
import { BizdevWorkflow } from './constructs/workflow/bizdev-workflow';

// 新しいインフラストラクチャコンストラクトのインポート
import { StorageResources } from './constructs/infrastructure/storage-resources';
import { MessagingResources } from './constructs/infrastructure/messaging-resources';
import { LambdaResources } from './constructs/infrastructure/lambda-resources';

export interface BizDevWorkflowStackProps extends cdk.StackProps {
  envName: string;
  projectName: string;
  notificationEmail?: string;
}

export class BizDevWorkflowStack extends cdk.Stack {
  public readonly agentStateTable: dynamodb.Table;
  public readonly messageHistoryTable: dynamodb.Table;
  public readonly artifactsBucket: s3.Bucket;
  
  public readonly agentCommunicationQueue: sqs.Queue;
  public readonly notificationTopic: sns.Topic;
  public readonly eventBus: events.EventBus;
  
  public readonly productManagerLambda: lambda.Function;
  public readonly architectLambda: lambda.Function;
  public readonly engineerLambda: lambda.Function;
  public readonly lambdaLayer: lambda.LayerVersion;
  public readonly apiEndpoint: string;
  // public readonly apiLambdaConstruct: ApiLambda;
  public readonly stateMachine: stepfunctions.StateMachine;
  public readonly apiLambdaFunctionName: string;

  constructor(scope: Construct, id: string, props: BizDevWorkflowStackProps) {
    super(scope, id, props);

    const { envName, projectName, notificationEmail } = props;

    // プレフィックスの定義
    const resourcePrefix = 'bizdev-wf-';

    // ===== 基本インフラストラクチャリソース =====
    // CloudWatch Logsグループ
    const applicationLogs = new logs.LogGroup(this, 'ApplicationLogs', {
      logGroupName: `/aws/${resourcePrefix}${projectName}/${envName}/application`,
      retention: envName === 'prod' ? logs.RetentionDays.ONE_MONTH : logs.RetentionDays.ONE_WEEK,
      removalPolicy: envName === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // ===== ストレージリソースコンストラクト =====
    const storageResources = new StorageResources(this, 'Storage', {
      envName,
      projectName,
      tableNamePrefix: resourcePrefix,
      bucketNamePrefix: resourcePrefix,
      account: this.account,
      region: this.region,
    });
    this.agentStateTable = storageResources.agentStateTable;
    this.messageHistoryTable = storageResources.messageHistoryTable;
    this.artifactsBucket = storageResources.artifactsBucket;

    // ===== メッセージングリソースコンストラクト =====
    const messagingResources = new MessagingResources(this, 'Messaging', {
      envName,
      projectName,
      queueNamePrefix: resourcePrefix,
      topicNamePrefix: resourcePrefix,
      eventBusNamePrefix: resourcePrefix,
      notificationEmail,
    });
    this.agentCommunicationQueue = messagingResources.agentCommunicationQueue;
    this.notificationTopic = messagingResources.notificationTopic;
    this.eventBus = messagingResources.eventBus;

    // ===== Lambda リソースコンストラクト =====
    const lambdaResources = new LambdaResources(this, 'Lambda', {
      envName,
      projectName,
      namePrefix: resourcePrefix,
    });
    this.lambdaLayer = lambdaResources.lambdaLayer;

    // ===== エージェントリソース =====
    // Product Manager Lambda
    const productManager = new ProductManager(this, 'ProductManager', {
      envName,
      projectName,
      lambdaLayer: this.lambdaLayer,
      agentStateTable: this.agentStateTable,
      messageHistoryTable: this.messageHistoryTable,
      artifactsBucket: this.artifactsBucket,
      agentCommunicationQueue: this.agentCommunicationQueue,
      eventBus: this.eventBus,
    });
    this.productManagerLambda = productManager.productManagerLambda;

    // Architect Lambda
    const architect = new Architect(this, 'Architect', {
      envName,
      projectName,
      lambdaLayer: this.lambdaLayer,
      agentStateTable: this.agentStateTable,
      messageHistoryTable: this.messageHistoryTable,
      artifactsBucket: this.artifactsBucket,
      agentCommunicationQueue: this.agentCommunicationQueue,
      eventBus: this.eventBus,
    });
    this.architectLambda = architect.architectLambda;

    // Engineer Lambda
    const engineer = new Engineer(this, 'Engineer', {
      envName,
      projectName,
      lambdaLayer: this.lambdaLayer,
      agentStateTable: this.agentStateTable,
      messageHistoryTable: this.messageHistoryTable,
      artifactsBucket: this.artifactsBucket,
      agentCommunicationQueue: this.agentCommunicationQueue,
      eventBus: this.eventBus,
    });
    this.engineerLambda = engineer.engineerLambda;

    // Workflow Construct
    const workflowConstruct = new BizdevWorkflow(this, 'PdmArchEngWorkflow', {
      envName,
      projectName,
      productManagerLambda: this.productManagerLambda,
      architectLambda: this.architectLambda,
      engineerLambda: this.engineerLambda,
    });
    this.stateMachine = workflowConstruct.stateMachine;

    // // API Lambda
    // this.apiLambdaConstruct = new ApiLambda(this, 'ApiLambda', {
    //   envName,
    //   projectName,
    //   lambdaLayer: this.lambdaLayer,
    //   agentCommunicationQueue: this.agentCommunicationQueue,
    //   eventBus: this.eventBus,
    // });
    // this.apiEndpoint = this.apiLambdaConstruct.apiEndpoint;
    
    // // APIにStateMachineを設定
    // this.apiLambdaConstruct.setStateMachine(this.stateMachine);

    // ===== 出力 =====
    // StorageStack 出力
    new cdk.CfnOutput(this, 'AgentStateTableName', {
      value: this.agentStateTable.tableName,
      description: 'Agent State DynamoDB Table Name',
      exportName: `${projectName}-${envName}-agent-state-table-name`,
    });

    new cdk.CfnOutput(this, 'MessageHistoryTableName', {
      value: this.messageHistoryTable.tableName,
      description: 'Message History DynamoDB Table Name',
      exportName: `${projectName}-${envName}-message-history-table-name`,
    });

    new cdk.CfnOutput(this, 'ArtifactsBucketName', {
      value: this.artifactsBucket.bucketName,
      description: 'Artifacts S3 Bucket Name',
      exportName: `${projectName}-${envName}-artifacts-bucket-name`,
    });

    // MessagingStack 出力
    new cdk.CfnOutput(this, 'AgentCommunicationQueueUrl', {
      value: this.agentCommunicationQueue.queueUrl,
      description: 'Agent Communication SQS Queue URL',
      exportName: `${projectName}-${envName}-agent-communication-queue-url`,
    });

    new cdk.CfnOutput(this, 'NotificationTopicArn', {
      value: this.notificationTopic.topicArn,
      description: 'Notification SNS Topic ARN',
      exportName: `${projectName}-${envName}-notification-topic-arn`,
    });

    new cdk.CfnOutput(this, 'EventBusArn', {
      value: this.eventBus.eventBusArn,
      description: 'Agent Event Bus ARN',
      exportName: `${projectName}-${envName}-event-bus-arn`,
    });

    new cdk.CfnOutput(this, 'StateMachineArn', {
      value: this.stateMachine.stateMachineArn,
      description: 'Agent Workflow State Machine ARN',
      exportName: `${projectName}-${envName}-state-machine-arn`,
    });

    // AgentsStack 出力
    new cdk.CfnOutput(this, 'LambdaLayerArn', {
      value: this.lambdaLayer.layerVersionArn,
      description: 'Common Lambda Layer ARN',
      exportName: `${projectName}-${envName}-lambda-layer-arn`,
    });

    new cdk.CfnOutput(this, 'ProductManagerLambdaArn', {
      value: this.productManagerLambda.functionArn,
      description: 'Product Manager Lambda Function ARN',
      exportName: `${projectName}-${envName}-product-manager-lambda-arn`,
    });

    new cdk.CfnOutput(this, 'ArchitectLambdaArn', {
      value: this.architectLambda.functionArn,
      description: 'Architect Lambda Function ARN',
      exportName: `${projectName}-${envName}-architect-lambda-arn`,
    });

    new cdk.CfnOutput(this, 'EngineerLambdaArn', {
      value: this.engineerLambda.functionArn,
      description: 'Engineer Lambda Function ARN',
      exportName: `${projectName}-${envName}-engineer-lambda-arn`,
    });
  }
}
