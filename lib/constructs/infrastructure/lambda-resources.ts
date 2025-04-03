import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface LambdaResourcesProps {
  envName: string;
  projectName: string;
  namePrefix: string;
}

export class LambdaResources extends Construct {
  public readonly lambdaLayer: lambda.LayerVersion;
  public readonly llmProxyLambda: lambda.Function;

  constructor(scope: Construct, id: string, props: LambdaResourcesProps) {
    super(scope, id);

    const { envName, projectName, namePrefix = '' } = props;

    // 共通のLambdaレイヤー
    this.lambdaLayer = new lambda.LayerVersion(this, 'CommonLayer', {
      code: lambda.Code.fromAsset('lambda/layers/common'),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_13],
      description: 'Common libraries for Lambda functions',
      layerVersionName: `${namePrefix}${projectName}-${envName}-lambda-layer`,
    });

    // カスタムLambda実行ロールを作成（AWS管理ポリシーの代わり）
    const lambdaExecutionRole = new iam.Role(this, 'LambdaExecutionRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Custom execution role for Lambda functions',
      roleName: `${namePrefix}${projectName}-${envName}-lambda-execution-role`,
    });

    // CloudWatch Logsへの書き込み権限を追加（AWSLambdaBasicExecutionRoleの代わり）
    lambdaExecutionRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'logs:CreateLogGroup',
          'logs:CreateLogStream',
          'logs:PutLogEvents'
        ],
        resources: [
          `arn:aws:logs:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:log-group:/aws/lambda/${namePrefix}${projectName}-${envName}*:*`
        ],
        sid: 'CloudWatchLogsAccess',
      })
    );

    // LLMプロキシLambda関数
    this.llmProxyLambda = new lambda.Function(this, 'LlmProxyFunction', {
      runtime: lambda.Runtime.PYTHON_3_13,
      code: lambda.Code.fromAsset('lambda/llm-proxy'),
      handler: 'index.handler',
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      environment: {
        ENV_NAME: envName,
        PROJECT_NAME: projectName,
      },
      layers: [this.lambdaLayer],
      functionName: `${namePrefix}${projectName}-${envName}-llm-proxy`,
      role: lambdaExecutionRole, // カスタム実行ロールを使用
    });

    // Bedrockへのアクセス権限を追加
    this.llmProxyLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['arn:aws:bedrock:*:*:foundation-model/*'],
        sid: 'BedrockInvokeModelAccess',
      })
    );
  }
}
