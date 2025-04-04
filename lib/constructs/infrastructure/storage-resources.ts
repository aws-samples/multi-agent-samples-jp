import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface StorageResourcesProps {
  envName: string;
  projectName: string;
  tableNamePrefix: string;
  bucketNamePrefix: string;
  account: string;
  region: string;
}

export class StorageResources extends Construct {
  public readonly agentStateTable: dynamodb.Table;
  public readonly messageHistoryTable: dynamodb.Table;
  public readonly artifactsBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: StorageResourcesProps) {
    super(scope, id);

    const { 
      envName, 
      projectName, 
      tableNamePrefix = '', 
      bucketNamePrefix = '',
      account,
      region
    } = props;

    // エージェント状態を保存するDynamoDBテーブル
    this.agentStateTable = new dynamodb.Table(this, 'AgentStateTable', {
      tableName: `${tableNamePrefix}${projectName}-${envName}-agent-state`,
      partitionKey: { name: 'agentId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'stateId', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: envName === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true }, // AwsSolutions-DDB3: PITRを有効化
    });

    // メッセージ履歴を保存するDynamoDBテーブル
    this.messageHistoryTable = new dynamodb.Table(this, 'MessageHistoryTable', {
      tableName: `${tableNamePrefix}${projectName}-${envName}-message-history`,
      partitionKey: { name: 'conversationId', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'timestamp', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: envName === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true }, // AwsSolutions-DDB3: PITRを有効化
      timeToLiveAttribute: 'ttl',
    });

    // 成果物を保存するS3バケット
    this.artifactsBucket = new s3.Bucket(this, 'ArtifactsBucket', {
      // bucketName: `${bucketNamePrefix}${projectName}-${envName}-artifacts-${account}-${region}`.toLowerCase(),
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      removalPolicy: envName === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: envName !== 'prod',
      versioned: envName === 'prod',
      serverAccessLogsPrefix: 'access-logs/', // AwsSolutions-S1: サーバーアクセスログを有効化
      enforceSSL: true, // AwsSolutions-S10: SSLを強制
      lifecycleRules: [
        {
          id: 'expire-old-versions',
          enabled: true,
          noncurrentVersionExpiration: cdk.Duration.days(30),
        },
      ],
    });
  }
}
