import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';
import { CloudFormationAnalysis } from './constructs/event-driven/cloudformation-analysis';
import { CloudArchitectLambda } from './constructs/agent/aws/cloud-architect';

// 新しいインフラストラクチャコンストラクトのインポート
import { StorageResources } from './constructs/infrastructure/storage-resources';
import { MessagingResources } from './constructs/infrastructure/messaging-resources';
import { LambdaResources } from './constructs/infrastructure/lambda-resources';

export interface CFnAnalysisEventDrivenStackProps extends cdk.StackProps {
  envName: string;
  projectName: string;
  notificationEmail?: string;
}

export class CFnAnalysisEventDrivenStack extends cdk.Stack {
  public readonly cloudFormationAnalysis: CloudFormationAnalysis;
  public readonly cloudArchitectLambda: lambda.Function;
  public readonly notificationTopic: cdk.aws_sns.Topic;

  constructor(scope: Construct, id: string, props: CFnAnalysisEventDrivenStackProps) {
    super(scope, id, props);

    const {
      envName,
      projectName,
      notificationEmail
    } = props;

    // プレフィックスの定義
    const resourcePrefix = 'cfnfa-ed-';

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
    const agentStateTable = storageResources.agentStateTable;
    const messageHistoryTable = storageResources.messageHistoryTable;
    const artifactsBucket = storageResources.artifactsBucket;

    // ===== メッセージングリソースコンストラクト =====
    const messagingResources = new MessagingResources(this, 'Messaging', {
      envName,
      projectName,
      queueNamePrefix: resourcePrefix,
      topicNamePrefix: resourcePrefix,
      eventBusNamePrefix: resourcePrefix,
      notificationEmail,
    });
    const agentCommunicationQueue = messagingResources.agentCommunicationQueue;
    this.notificationTopic = messagingResources.notificationTopic;
    const eventBus = messagingResources.eventBus;

    // ===== Lambda リソースコンストラクト =====
    const lambdaResources = new LambdaResources(this, 'Lambda', {
      envName,
      projectName,
      namePrefix: resourcePrefix,
    });
    const lambdaLayer = lambdaResources.lambdaLayer;

    // Cloud Architect Lambda
    const cloudArchitectLambdaConstruct = new CloudArchitectLambda(this, 'CloudArchitectLambda', {
      envName,
      projectName,
      lambdaLayer,
      agentStateTable,
      messageHistoryTable,
      artifactsBucket,
      agentCommunicationQueue,
      eventBus,
    });
    this.cloudArchitectLambda = cloudArchitectLambdaConstruct.cloudArchitectLambda;

    // CloudArchitectエージェントにCloudFormationへのアクセス権限を付与
    this.cloudArchitectLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'cloudformation:DescribeStacks',
          'cloudformation:DescribeStackEvents',
          'cloudformation:DescribeStackResources',
          'cloudformation:GetTemplate'
        ],
        resources: ['*'],
      })
    );

    // CloudFormation失敗分析ワークフロー
    this.cloudFormationAnalysis = new CloudFormationAnalysis(this, 'CFnFA', {
      envName,
      projectName,
      cloudArchitectLambda: this.cloudArchitectLambda,
      notificationTopic: this.notificationTopic,
      notificationEmail,
    });

    // 出力
    new cdk.CfnOutput(this, 'CFnFAStateMachineArn', {
      value: this.cloudFormationAnalysis.stateMachine.stateMachineArn,
      description: 'CloudFormation Analysis State Machine ARN',
      exportName: `${projectName}-${envName}-cfn-fa-state-machine-arn`,
    });

    new cdk.CfnOutput(this, 'CFnEventRuleArn', {
      value: this.cloudFormationAnalysis.eventRule.ruleArn,
      description: 'CloudFormation Event Rule ARN',
      exportName: `${projectName}-${envName}-cfn--event-rule-arn`,
    });

    new cdk.CfnOutput(this, 'CloudArchitectLambdaArn', {
      value: this.cloudArchitectLambda.functionArn,
      description: 'Cloud Architect Lambda Function ARN for CloudFormation Analysis',
      exportName: `${projectName}-${envName}-cfn-cloud-architect-lambda-arn`,
    });
  }
}
