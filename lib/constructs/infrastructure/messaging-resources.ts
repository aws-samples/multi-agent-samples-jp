import * as cdk from 'aws-cdk-lib';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as events from 'aws-cdk-lib/aws-events';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as sns_subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface MessagingResourcesProps {
  envName: string;
  projectName: string;
  queueNamePrefix: string;
  topicNamePrefix: string;
  eventBusNamePrefix: string;
  notificationEmail?: string;
}

export class MessagingResources extends Construct {
  public readonly agentCommunicationQueue: sqs.Queue;
  public readonly deadLetterQueue: sqs.Queue;
  public readonly failedMessageQueue: sqs.Queue;
  public readonly notificationTopic: sns.Topic;
  public readonly eventBus: events.EventBus;
  public readonly stateMachine: stepfunctions.StateMachine;

  constructor(scope: Construct, id: string, props: MessagingResourcesProps) {
    super(scope, id);

    const { 
      envName, 
      projectName, 
      queueNamePrefix = '', 
      topicNamePrefix = '',
      eventBusNamePrefix = '',
      notificationEmail
    } = props;

    // デッドレターキュー
    this.deadLetterQueue = new sqs.Queue(this, 'DeadLetterQueue', {
      queueName: `${queueNamePrefix}${projectName}-${envName}-dead-letter`,
      retentionPeriod: cdk.Duration.days(14),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      enforceSSL: true, // AwsSolutions-SQS4: SSLを強制
    });

    // エージェント間通信用のSQSキュー
    this.agentCommunicationQueue = new sqs.Queue(this, 'AgentCommunicationQueue', {
      queueName: `${queueNamePrefix}${projectName}-${envName}-agent-communication`,
      visibilityTimeout: cdk.Duration.minutes(5),
      retentionPeriod: cdk.Duration.days(4),
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      enforceSSL: true, // AwsSolutions-SQS4: SSLを強制
      deadLetterQueue: { // AwsSolutions-SQS3: DLQを設定
        queue: this.deadLetterQueue,
        maxReceiveCount: 3,
      },
    });

    // 失敗したメッセージ用のキュー
    this.failedMessageQueue = new sqs.Queue(this, 'FailedMessageQueue', {
      queueName: `${queueNamePrefix}${projectName}-${envName}-failed-messages`,
      visibilityTimeout: cdk.Duration.minutes(5),
      retentionPeriod: cdk.Duration.days(7),
      deadLetterQueue: {
        queue: this.deadLetterQueue,
        maxReceiveCount: 3,
      },
      encryption: sqs.QueueEncryption.SQS_MANAGED,
      enforceSSL: true, // AwsSolutions-SQS4: SSLを強制
    });

    // 通知用のSNSトピック
    this.notificationTopic = new sns.Topic(this, 'NotificationTopic', {
      topicName: `${topicNamePrefix}${projectName}-${envName}-notifications`,
      displayName: `${projectName.toUpperCase()} ${envName} Notifications`,
      enforceSSL: true, // AwsSolutions-SNS3: SSLを強制
    });

    // メール通知が指定されていれば、SNSトピックにサブスクリプションを追加
    if (notificationEmail) {
      this.notificationTopic.addSubscription(
        new sns_subscriptions.EmailSubscription(notificationEmail)
      );
    }

    // イベントバス
    this.eventBus = new events.EventBus(this, 'AgentEventBus', {
      eventBusName: `${eventBusNamePrefix}${projectName}-${envName}-agent-events`,
    });

    // 失敗したメッセージを通知するSNSサブスクリプション
    this.notificationTopic.addSubscription(
      new sns_subscriptions.SqsSubscription(this.failedMessageQueue)
    );

    // イベントルール
    new events.Rule(this, 'AgentFailureRule', {
      eventBus: this.eventBus,
      ruleName: `${eventBusNamePrefix}${projectName}-${envName}-agent-failure`,
      description: 'Rule for agent failures',
      eventPattern: {
        source: ['agent.system'],
        detailType: ['AgentFailure'],
      },
      targets: [
        new targets.SnsTopic(this.notificationTopic, {
          message: events.RuleTargetInput.fromText(
            `Agent failure detected: ${events.EventField.fromPath('$.detail.agentId')} - ${events.EventField.fromPath('$.detail.errorMessage')}`
          ),
        }),
      ],
    });
  }
}
