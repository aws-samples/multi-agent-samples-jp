import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';

import { PropertyTarget, InverseDesign, ExperimentPlanning } from './constructs/agent/materials';
import { MaterialsWorkflow } from './constructs/workflow/materials-workflow';

export interface MaterialsWorkflowStackProps extends cdk.StackProps {
  envName: string;
  projectName: string;
}

export class MaterialsWorkflowStack extends cdk.Stack {
  public readonly propertyTargetAlias: bedrock.AgentAlias;
  public readonly inverseDesignAlias: bedrock.AgentAlias;
  public readonly experimentPlanningAlias: bedrock.AgentAlias;

  constructor(scope: Construct, id: string, props: MaterialsWorkflowStackProps) {
    super(scope, id, props);

    const { envName, projectName } = props;

    // 共有リソースの作成
    // DynamoDBテーブル
    const agentStateTable = new dynamodb.Table(this, 'AgentStateTable', {
      tableName: `${projectName}-${envName}-agent-state`,
      partitionKey: { name: 'SessionId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'Timestamp', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    });

    const messageHistoryTable = new dynamodb.Table(this, 'MessageHistoryTable', {
      tableName: `${projectName}-${envName}-message-history`,
      partitionKey: { name: 'MessageId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: {
        pointInTimeRecoveryEnabled: true,
      },
    });

    // S3バケット
    const artifactsBucket = new s3.Bucket(this, 'ArtifactsBucket', {
      bucketName: `${projectName}-${envName}-artifacts-${this.account}-${this.region}`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      serverAccessLogsPrefix: 'access-logs/',
      enforceSSL: true,
    });

    // SQSキュー
    const deadLetterQueue = new sqs.Queue(this, 'DeadLetterQueue', {
      queueName: `${projectName}-${envName}-agent-communication-dlq`,
      retentionPeriod: cdk.Duration.days(14),
      enforceSSL: true,
    });

    const agentCommunicationQueue = new sqs.Queue(this, 'AgentCommunicationQueue', {
      queueName: `${projectName}-${envName}-agent-communication`,
      visibilityTimeout: cdk.Duration.seconds(300),
      retentionPeriod: cdk.Duration.days(14),
      enforceSSL: true,
      deadLetterQueue: {
        maxReceiveCount: 3,
        queue: deadLetterQueue,
      },
    });

    // EventBridge
    const eventBus = new events.EventBus(this, 'EventBus', {
      eventBusName: `${projectName}-${envName}-event-bus`,
    });

    // 共通Lambda Layer
    const commonLayer = new lambda.LayerVersion(this, 'CommonLayer', {
      code: lambda.Code.fromAsset('lambda/layers/common'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Common utilities for agent Lambda functions',
    });

    // エージェントの作成
    const propertyTarget = new PropertyTarget(this, 'PropertyTarget', {
      envName,
      projectName,
      lambdaLayer: commonLayer,
      agentStateTable,
      messageHistoryTable,
      artifactsBucket,
      agentCommunicationQueue,
      eventBus,
    });

    const inverseDesign = new InverseDesign(this, 'InverseDesign', {
      envName,
      projectName,
      lambdaLayer: commonLayer,
      agentStateTable,
      messageHistoryTable,
      artifactsBucket,
      agentCommunicationQueue,
      eventBus,
    });

    const experimentPlanning = new ExperimentPlanning(this, 'ExperimentPlanning', {
      envName,
      projectName,
      lambdaLayer: commonLayer,
      agentStateTable,
      messageHistoryTable,
      artifactsBucket,
      agentCommunicationQueue,
      eventBus,
    });

    // エージェントのエイリアスを公開
    this.propertyTargetAlias = propertyTarget.propertyTargetAlias;
    this.inverseDesignAlias = inverseDesign.inverseDesignAlias;
    this.experimentPlanningAlias = experimentPlanning.experimentPlanningAlias;

    // ワークフローの作成
    const materialsWorkflow = new MaterialsWorkflow(this, 'MaterialsWorkflow', {
      envName,
      projectName,
      propertyTargetLambda: propertyTarget.propertyTargetLambda,
      inverseDesignLambda: inverseDesign.inverseDesignLambda,
      experimentPlanningLambda: experimentPlanning.experimentPlanningLambda,
    });

    // 出力
    new cdk.CfnOutput(this, 'PropertyTargetAgentAlias', {
      value: propertyTarget.propertyTargetAlias.aliasId,
      description: 'Property Target Agent Alias ID',
    });

    new cdk.CfnOutput(this, 'InverseDesignAgentAlias', {
      value: inverseDesign.inverseDesignAlias.aliasId,
      description: 'Inverse Design Agent Alias ID',
    });

    new cdk.CfnOutput(this, 'ExperimentPlanningAgentAlias', {
      value: experimentPlanning.experimentPlanningAlias.aliasId,
      description: 'Experiment Planning Agent Alias ID',
    });

    new cdk.CfnOutput(this, 'MaterialsWorkflowArn', {
      value: materialsWorkflow.stateMachine.stateMachineArn,
      description: 'Materials Workflow State Machine ARN',
    });

    new cdk.CfnOutput(this, 'ArtifactsBucketName', {
      value: artifactsBucket.bucketName,
      description: 'Artifacts S3 Bucket Name',
    });
  }
}
