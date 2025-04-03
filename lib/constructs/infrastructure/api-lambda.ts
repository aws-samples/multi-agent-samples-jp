import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';

export interface ApiLambdaProps {
  envName: string;
  projectName: string;
  lambdaLayer: lambda.LayerVersion;
  agentCommunicationQueue: sqs.Queue;
  eventBus: events.EventBus;
  resourcePrefix: string;
  stateMachine?: stepfunctions.StateMachine; // オプショナル
}

export class ApiLambda extends Construct {
  public readonly api: apigateway.RestApi;
  public readonly apiLambda: lambda.Function;
  public readonly apiEndpoint: string;

  constructor(scope: Construct, id: string, props: ApiLambdaProps) {
    super(scope, id);

    const {
      envName,
      projectName,
      lambdaLayer,
      agentCommunicationQueue,
      eventBus,
      stateMachine
    } = props;
    
    // CloudWatch Logsへのアクセス権を持つロールを作成
    const apiGatewayLoggingRole = new iam.Role(this, 'ApiGatewayLoggingRole', {
      assumedBy: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonAPIGatewayPushToCloudWatchLogs')
      ]
    });

    // API Gatewayのアカウント設定を更新
    const apiGatewayAccount = new apigateway.CfnAccount(this, 'ApiGatewayAccount', {
      cloudWatchRoleArn: apiGatewayLoggingRole.roleArn
    });

    // API Gateway
    this.api = new apigateway.RestApi(this, 'AgentApi', {
      restApiName: `${projectName}-${envName}-api`,
      description: 'API for interacting with agent framework',
      deployOptions: {
        stageName: envName,
        loggingLevel: apigateway.MethodLoggingLevel.INFO,
        dataTraceEnabled: true,
        metricsEnabled: true,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'X-Api-Key'],
      },
    });
    
    // 重要: API Gatewayリソースが作成される前にアカウント設定が適用されるようにする
    this.api.node.addDependency(apiGatewayAccount);

    // 環境変数の設定
    const lambdaEnv: {[key: string]: string} = {
      ENV_NAME: envName,
      PROJECT_NAME: projectName,
      COMMUNICATION_QUEUE_URL: agentCommunicationQueue.queueUrl,
      EVENT_BUS_NAME: eventBus.eventBusName,
      ACCOUNT_ID: cdk.Stack.of(this).account,
    };

    // StateMachineが提供されている場合は環境変数に追加
    if (stateMachine) {
      lambdaEnv['STATE_MACHINE_ARN'] = stateMachine.stateMachineArn;
    }

    // API Lambda関数
    this.apiLambda = new lambda.Function(this, 'ApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/api'),
      handler: 'index.handler',
      timeout: cdk.Duration.minutes(5),
      memorySize: 1024,
      environment: lambdaEnv,
      layers: [lambdaLayer],
    });

    // SQSへのアクセス権限を追加
    agentCommunicationQueue.grantSendMessages(this.apiLambda);

    // EventBridgeへのアクセス権限を追加
    eventBus.grantPutEventsTo(this.apiLambda);

    // StateMachineが提供されている場合は権限を付与
    if (stateMachine) {
      stateMachine.grantStartExecution(this.apiLambda);
      stateMachine.grantRead(this.apiLambda);
    }

    // API Gateway統合
    const apiIntegration = new apigateway.LambdaIntegration(this.apiLambda);

    // APIリソースとメソッド
    const agentsResource = this.api.root.addResource('agents');
    
    // GET /agents - エージェント一覧を取得
    agentsResource.addMethod('GET', apiIntegration);
    
    // POST /agents - 新しいエージェントを作成
    agentsResource.addMethod('POST', apiIntegration);

    // エージェント個別のリソース
    const agentResource = agentsResource.addResource('{agentId}');
    
    // GET /action_group/{agentId} - 特定のエージェント情報を取得
    agentResource.addMethod('GET', apiIntegration);

    // タスクリソース
    const tasksResource = this.api.root.addResource('tasks');
    
    // POST /tasks - 新しいタスクを作成
    tasksResource.addMethod('POST', apiIntegration);
    
    // GET /tasks - タスク一覧を取得
    tasksResource.addMethod('GET', apiIntegration);

    // タスク個別のリソース
    const taskResource = tasksResource.addResource('{taskId}');
    
    // GET /tasks/{taskId} - 特定のタスク情報を取得
    taskResource.addMethod('GET', apiIntegration);

    this.apiEndpoint = this.api.url;
  }

  // StateMachineを後から設定するためのメソッド
  public setStateMachine(stateMachine: stepfunctions.StateMachine) {
    // 環境変数を更新
    this.apiLambda.addEnvironment('STATE_MACHINE_ARN', stateMachine.stateMachineArn);
    
    // 権限の付与
    stateMachine.grantStartExecution(this.apiLambda);
    stateMachine.grantRead(this.apiLambda);
  }
}