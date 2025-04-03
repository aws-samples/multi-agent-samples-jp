import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Construct } from 'constructs';

export interface BizdevWorkflowProps {
  envName: string;
  projectName: string;
  productManagerLambda: lambda.Function;
  architectLambda: lambda.Function;
  engineerLambda: lambda.Function;
}

export class BizdevWorkflow extends Construct {
  public readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: BizdevWorkflowProps) {
    super(scope, id);

    const { envName, projectName, productManagerLambda, architectLambda, engineerLambda } = props;

    // ステートマシンのロール
    const stateMachineRole = new iam.Role(this, 'StateMachineRole', {
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
      description: 'Role for Agent Workflow State Machine',
    });
    
    // Lambda関数を呼び出す権限を追加
    productManagerLambda.grantInvoke(stateMachineRole);
    architectLambda.grantInvoke(stateMachineRole);
    engineerLambda.grantInvoke(stateMachineRole);
    
    // Step Functions定義を作成
    // 初期化ステート - プロジェクトIDを生成し、必要なフィールドを確保
    const initialize = new sfn.Pass(this, 'Initialize', {
      parameters: {
        'status': 'initialized',
        'project_id.$': '$$.Execution.Name', // Step Functions実行IDをプロジェクトIDとして使用
        'requirement.$': '$.requirement',
        'task_type': 'software_development',
        'user_id.$': '$.user_id',
        'timestamp.$': '$$.Execution.StartTime'
      },
    });
    
    // 要件分析ステート
    const processRequirement = new tasks.LambdaInvoke(this, 'ProcessRequirement', {
      lambdaFunction: productManagerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'analyze_requirement',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.analysis_result',
    });
    
    // ユーザーストーリー作成ステート
    const createUserStories = new tasks.LambdaInvoke(this, 'CreateUserStories', {
      lambdaFunction: productManagerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'create_user_stories',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'analysis_id.$': '$.analysis_result.Payload.analysis_id',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.user_stories_result',
    });
    
    // 競合分析ステート
    const createCompetitiveAnalysis = new tasks.LambdaInvoke(this, 'CreateCompetitiveAnalysis', {
      lambdaFunction: productManagerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'create_competitive_analysis',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.competitive_analysis_result',
    });
    
    // PRD作成ステート
    const createPRD = new tasks.LambdaInvoke(this, 'CreatePRD', {
      lambdaFunction: productManagerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'create_product_requirement_doc',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'stories_id.$': '$.user_stories_result.Payload.stories_id',
        'competitive_analysis_id.$': '$.competitive_analysis_result.Payload.analysis_id',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.prd_result',
    });
    
    // アーキテクチャ作成ステート
    const createArchitecture = new tasks.LambdaInvoke(this, 'CreateArchitecture', {
      lambdaFunction: architectLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'create_architecture',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'prd_id.$': '$.prd_result.Payload.prd_id',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.architecture_result',
    });
    
    // コード実装ステート
    const implementCode = new tasks.LambdaInvoke(this, 'ImplementCode', {
      lambdaFunction: engineerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'implement_code',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'prd_id.$': '$.prd_result.Payload.prd_id',
        'architecture_id.$': '$.architecture_result.Payload.architecture_id',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.implementation_result',
    });
    
    // コードレビューステート
    const reviewCode = new tasks.LambdaInvoke(this, 'ReviewCode', {
      lambdaFunction: engineerLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'review_code',
        'project_id.$': '$.project_id',
        'requirement.$': '$.requirement',
        'implementation_id.$': '$.implementation_result.Payload.implementation_id',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.review_result',
    });
    
    // エラーハンドリングステート
    const handleError = new sfn.Pass(this, 'HandleError', {
      result: sfn.Result.fromObject({
        status: 'failed',
        message: 'Workflow execution failed'
      }),
    });
    
    // 成功・失敗ステート
    const success = new sfn.Succeed(this, 'Success');
    const fail = new sfn.Fail(this, 'Fail');
    
    // ステートの接続
    initialize.next(processRequirement);
    processRequirement.next(createUserStories);
    createUserStories.next(createCompetitiveAnalysis);
    createCompetitiveAnalysis.next(createPRD);
    createPRD.next(createArchitecture);
    createArchitecture.next(implementCode);
    implementCode.next(reviewCode);
    reviewCode.next(success);
    handleError.next(fail);
    
    // エラーキャッチ
    processRequirement.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    createUserStories.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    createCompetitiveAnalysis.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    createPRD.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    createArchitecture.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    implementCode.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    reviewCode.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    // ステートマシンを作成
    this.stateMachine = new sfn.StateMachine(this, 'AgentWorkflow', {
      stateMachineName: `${projectName}-${envName}-main-workflow`,
      definitionBody: sfn.DefinitionBody.fromChainable(initialize),
      role: stateMachineRole,
      timeout: cdk.Duration.hours(24),
      tracingEnabled: true,
      logs: {
        destination: new logs.LogGroup(this, 'StateMachineLogs', {
          logGroupName: `/aws/states/${projectName}-${envName}-main-workflow`,
          removalPolicy: cdk.RemovalPolicy.DESTROY,
        }),
        level: sfn.LogLevel.ALL,
      },
    });
  }
}