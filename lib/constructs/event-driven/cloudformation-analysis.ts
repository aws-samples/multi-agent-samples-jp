import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as stepfunctions from 'aws-cdk-lib/aws-stepfunctions';
import * as stepfunctionsTasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import { Construct } from 'constructs';
import * as path from 'path';

export interface CloudFormationAnalysisProps {
  envName: string;
  projectName: string;
  cloudArchitectLambda: lambda.Function;
  notificationTopic?: sns.Topic;
  notificationEmail?: string;
}

export class CloudFormationAnalysis extends Construct {
  public readonly stateMachine: stepfunctions.StateMachine;
  public readonly eventRule: events.Rule;

  constructor(scope: Construct, id: string, props: CloudFormationAnalysisProps) {
    super(scope, id);

    const {
      envName,
      projectName,
      cloudArchitectLambda,
      notificationTopic,
      notificationEmail
    } = props;

    // 通知用のSNSトピック（指定がなければ新規作成）
    const cfnAnalysisTopic = notificationTopic || new sns.Topic(this, 'FANotificationTopic', {
      topicName: `${projectName}-${envName}-cfn-analysis-notifications`,
      displayName: `${projectName.toUpperCase()} ${envName} CloudFormation Analysis Notifications`,
    });

    // メール通知が指定されていれば、SNSトピックにサブスクリプションを追加
    if (notificationEmail && !notificationTopic) {
      cfnAnalysisTopic.addSubscription(
        new subscriptions.EmailSubscription(notificationEmail)
      );
    }

    // CloudFormationイベントを解析するLambda関数
    // カスタムLambda実行ロールを作成（AWS管理ポリシーの代わり）
    const cfnEventParserRole = new iam.Role(this, 'CfnEventParserRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for CloudFormation Event Parser Lambda function',
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    cfnEventParserRole.addToPolicy(
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

    const cfnEventParserLambda = new lambda.Function(this, 'CfnEventParserFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../lambda/action_group/aws/cfn-event-parser')),
      handler: 'index.handler',
      timeout: cdk.Duration.seconds(30),
      memorySize: 128,
      environment: {
        ENV_NAME: envName,
        PROJECT_NAME: projectName,
      },
      role: cfnEventParserRole, // カスタム実行ロールを使用
    });

    // CloudFormationイベントを解析するLambda関数にCloudFormationの読み取り権限を付与
    cfnEventParserRole.addToPolicy(
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

    // Step Functions定義
    // 1. CloudFormationイベントを解析
    const parseCfnEvent = new stepfunctionsTasks.LambdaInvoke(this, 'ParseCfnEvent', {
      lambdaFunction: cfnEventParserLambda,
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // 2. CloudArchitectエージェントを呼び出して失敗分析を実行
    const invokeCloudArchitect = new stepfunctionsTasks.LambdaInvoke(this, 'InvokeCloudArchitect', {
      lambdaFunction: cloudArchitectLambda,
      payload: stepfunctions.TaskInput.fromObject({
        process_type: 'design_cloud_architecture',
        requirement: stepfunctions.JsonPath.format(
          'CloudFormation Stack Change Analysis: Stack Name: {}. Logical Resource ID: {}. Resource Type: {}. Status Reason: {}. \n\nTemplate: {}\n\n. CFnのアーキテクチャを解説して下さい。出力は絶対に日本語でお願いします。',
          stepfunctions.JsonPath.stringAt('$.stackName'),
          stepfunctions.JsonPath.stringAt('$.logicalResourceId'),
          stepfunctions.JsonPath.stringAt('$.resourceType'),
          stepfunctions.JsonPath.stringAt('$.statusReason'),
          stepfunctions.JsonPath.stringAt('$.template'),
        ),
        architecture_type: 'cfn template',
        project_id: stepfunctions.JsonPath.stringAt('$.stackId'),
      }),
      outputPath: '$.Payload',
      retryOnServiceExceptions: true,
    });

    // CloudArchitectの出力を通知用に変換するマッピングステップ
    const mapToNotification = new stepfunctions.Pass(this, 'MapToNotification', {
      parameters: {
        // CloudArchitectの出力から必要な情報を抽出し、通知用のフォーマットに変換
        stackId: stepfunctions.JsonPath.stringAt('$.project_id'),
        architecture_id: stepfunctions.JsonPath.stringAt('$.architecture_id'),
        s3_key: stepfunctions.JsonPath.stringAt('$.s3_key'),
        status: stepfunctions.JsonPath.stringAt('$.status'),
        project_id: stepfunctions.JsonPath.stringAt('$.project_id'),
        analysis_summary: stepfunctions.JsonPath.stringAt('$.cloud_architecture')
      }
    });

    // 3. 通知を送信
    const sendNotification = new stepfunctionsTasks.SnsPublish(this, 'SendNotification', {
      topic: cfnAnalysisTopic,
      message: stepfunctions.TaskInput.fromText(
        stepfunctions.JsonPath.format(
          'CloudFormation Stack Analysis\n\nStack ID: {}\n\nAnalysis ID: {}\n\nReview the analysis in the S3 bucket: {}\n\nStatus: {}\n\nSummary: {}',
          stepfunctions.JsonPath.stringAt('$.stackId'),
          stepfunctions.JsonPath.stringAt('$.architecture_id'),
          stepfunctions.JsonPath.stringAt('$.s3_key'),
          stepfunctions.JsonPath.stringAt('$.status'),
          stepfunctions.JsonPath.stringAt('$.analysis_summary')
        )
      ),
      subject: stepfunctions.JsonPath.format(
        '[{}] CloudFormation Stack Analysis',
        envName.toUpperCase()
      ),
    });

    // エラーハンドリング
    const handleError = new stepfunctionsTasks.SnsPublish(this, 'HandleError', {
      topic: cfnAnalysisTopic,
      message: stepfunctions.TaskInput.fromText(
        stepfunctions.JsonPath.format(
          'Error analyzing CloudFormation stack failure\n\nStack ID: {0}\n\nError: {1}\n\nExecution: {2}',
          stepfunctions.JsonPath.stringAt('$$.Execution.Input.detail.stack-id') || 'Unknown Stack',
          stepfunctions.JsonPath.stringAt('$.Error') || 'Unknown Error',
          stepfunctions.JsonPath.stringAt('$$.Execution.Id')
        )
      ),
      subject: stepfunctions.JsonPath.format(
        '[{0}] CloudFormation Failure Analysis Error',
        envName.toUpperCase()
      ),
    });

    // ワークフロー定義（エラーハンドリングを含む）
    const definition = parseCfnEvent
      .next(invokeCloudArchitect)
      .next(mapToNotification)
      .next(sendNotification);
      
    // エラーハンドリングを追加
    const catchProps: stepfunctions.CatchProps = {
      resultPath: '$.error',
      errors: ['States.ALL'],
    };
    
    // Step Functions ステートマシン
    this.stateMachine = new stepfunctions.StateMachine(this, 'CfnFAWorkflow', {
      stateMachineName: `${projectName}-${envName}-cfn-analysis`,
      definitionBody: stepfunctions.DefinitionBody.fromChainable(definition),
      timeout: cdk.Duration.minutes(30),
      tracingEnabled: true,
      logs: {
        destination: new cdk.aws_logs.LogGroup(this, 'StateMachineLogs', {
          logGroupName: `/aws/states/${projectName}-${envName}-cfn-analysis`,
          removalPolicy: cdk.RemovalPolicy.DESTROY,
        }),
        level: stepfunctions.LogLevel.ALL,
        includeExecutionData: true,
      },
    });

    // CloudFormationのスタック作成/更新失敗をキャッチするEventBridgeルール
    this.eventRule = new events.Rule(this, 'CfnStackAnalysisRule', {
      ruleName: `${projectName}-${envName}-cfn-stack-analysis`,
      description: 'Captures CloudFormation stack creation or update',
      eventPattern: {
        source: ['aws.cloudformation'],
        detailType: ['CloudFormation Stack Status Change'],
        // detail: {
        //   'status': ['ROLLBACK_COMPLETE']
        // }
      },
      targets: [
        new targets.SfnStateMachine(this.stateMachine)
      ]
    });

    // CloudWatchイベントがステートマシンを実行できるようにIAMポリシーを追加
    const eventBridgeRole = new iam.Role(this, 'EventBridgeRole', {
      assumedBy: new iam.ServicePrincipal('events.amazonaws.com'),
    });

    eventBridgeRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['states:StartExecution'],
        resources: [this.stateMachine.stateMachineArn],
      })
    );

    // 出力
    new cdk.CfnOutput(this, 'CfnAnalysisStateMachineArn', {
      value: this.stateMachine.stateMachineArn,
      description: 'CloudFormation Analysis State Machine ARN',
      exportName: `${projectName}-${envName}-cfn-analysis-state-machine-arn-construct`,
    });

    new cdk.CfnOutput(this, 'CfnAnalysisEventRuleArn', {
      value: this.eventRule.ruleArn,
      description: 'CloudFormation Analysis Event Rule ARN',
      exportName: `${projectName}-${envName}-cfn-analysis-event-rule-arn-construct`,
    });
  }
}
