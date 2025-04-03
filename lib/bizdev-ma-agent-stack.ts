import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';

import { StorageResources } from './constructs/infrastructure/storage-resources';
import { MessagingResources } from './constructs/infrastructure/messaging-resources';
import { LambdaResources } from './constructs/infrastructure/lambda-resources';
import { ProductManager } from './constructs/agent/bizdev/product-manager';
import { Architect } from './constructs/agent/bizdev/architect';
import { Engineer } from './constructs/agent/bizdev/engineer';

export interface BizDevMaStackProps extends cdk.StackProps {
  envName: string;
  projectName: string;
  notificationEmail?: string;
}

export class BizDevMaStack extends cdk.Stack {
  public readonly pdm_alias: bedrock.AgentAlias;
  public readonly architect_alias: bedrock.AgentAlias;
  public readonly engineer_alias: bedrock.AgentAlias;

  constructor(scope: Construct, id: string, props: BizDevMaStackProps) {
    super(scope, id, props);

    const { envName, projectName, notificationEmail } = props;

    // プレフィックスの定義
    const resourcePrefix = 'bizdev-ma-';

    // ストレージリソース
    const storage = new StorageResources(this, 'Storage', {
      envName,
      projectName,
      tableNamePrefix: resourcePrefix,
      bucketNamePrefix: resourcePrefix,
      account: this.account,
      region: this.region,
    });

    // メッセージングリソース
    const messaging = new MessagingResources(this, 'Messaging', {
      envName,
      projectName,
      queueNamePrefix: resourcePrefix,
      topicNamePrefix: resourcePrefix,
      eventBusNamePrefix: resourcePrefix,
      notificationEmail,
    });

    // Lambda共通リソース
    const lambda = new LambdaResources(this, 'Lambda', {
      envName,
      projectName,
      namePrefix: resourcePrefix,
    });

    // プロダクトマネージャー
    const productManager = new ProductManager(this, 'ProductManager', {
      envName,
      projectName,
      lambdaLayer: lambda.lambdaLayer,
      agentStateTable: storage.agentStateTable,
      messageHistoryTable: storage.messageHistoryTable,
      artifactsBucket: storage.artifactsBucket,
      agentCommunicationQueue: messaging.agentCommunicationQueue,
      eventBus: messaging.eventBus,
    });
    this.pdm_alias = productManager.productManagerAlias

    // アーキテクト
    const architect = new Architect(this, 'Architect', {
      envName,
      projectName,
      lambdaLayer: lambda.lambdaLayer,
      agentStateTable: storage.agentStateTable,
      messageHistoryTable: storage.messageHistoryTable,
      artifactsBucket: storage.artifactsBucket,
      agentCommunicationQueue: messaging.agentCommunicationQueue,
      eventBus: messaging.eventBus,
    });
    this.architect_alias = architect.architectAlias

    // エンジニア
    const engineer = new Engineer(this, 'Engineer', {
      envName,
      projectName,
      lambdaLayer: lambda.lambdaLayer,
      agentStateTable: storage.agentStateTable,
      messageHistoryTable: storage.messageHistoryTable,
      artifactsBucket: storage.artifactsBucket,
      agentCommunicationQueue: messaging.agentCommunicationQueue,
      eventBus: messaging.eventBus,
    });
    this.engineer_alias = engineer.engineerAlias
  }
}
