import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as sfn from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import { Construct } from 'constructs';

export interface MaterialsWorkflowProps {
  envName: string;
  projectName: string;
  propertyTargetLambda: lambda.Function;
  inverseDesignLambda: lambda.Function;
  experimentPlanningLambda: lambda.Function;
}

export class MaterialsWorkflow extends Construct {
  public readonly stateMachine: sfn.StateMachine;

  constructor(scope: Construct, id: string, props: MaterialsWorkflowProps) {
    super(scope, id);

    const { envName, projectName, propertyTargetLambda, inverseDesignLambda, experimentPlanningLambda } = props;

    // ステートマシンのロール
    const stateMachineRole = new iam.Role(this, 'StateMachineRole', {
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
      description: 'Role for Materials Workflow State Machine',
    });
    
    // Lambda関数を呼び出す権限を追加
    propertyTargetLambda.grantInvoke(stateMachineRole);
    inverseDesignLambda.grantInvoke(stateMachineRole);
    experimentPlanningLambda.grantInvoke(stateMachineRole);
    
    // Step Functions定義を作成
    // 初期化ステート - セッションIDを生成し、必要なフィールドを確保
    const initialize = new sfn.Pass(this, 'Initialize', {
      parameters: {
        'status': 'initialized',
        'session_id.$': '$$.Execution.Name', // Step Functions実行IDをセッションIDとして使用
        'requirements.$': '$.requirements',
        'user_id.$': '$.user_id',
        'timestamp.$': '$$.Execution.StartTime'
      },
    });
    
    // 特性目標設定ステート
    const propertyTargetSetting = new tasks.LambdaInvoke(this, 'PropertyTargetSetting', {
      lambdaFunction: propertyTargetLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'set_target_properties',
        'session_id.$': '$.session_id',
        'requirements.$': '$.requirements',
        'user_id.$': '$.user_id',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.property_target_result',
    });
    
    // 材料逆設計ステート
    const materialInverseDesign = new tasks.LambdaInvoke(this, 'MaterialInverseDesign', {
      lambdaFunction: inverseDesignLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'design_materials',
        'session_id.$': '$.session_id',
        'target_properties.$': '$.property_target_result.Payload.target_properties',
        'constraints': {
          'toxicity': 'low',
          'cost': 'medium',
          'rare_elements': 'avoid'
        },
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.inverse_design_result',
    });
    
    // 候補材料ランク付けステート
    const rankCandidates = new tasks.LambdaInvoke(this, 'RankCandidates', {
      lambdaFunction: inverseDesignLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'rank_candidates',
        'session_id.$': '$.session_id',
        'candidate_materials.$': '$.inverse_design_result.Payload.candidate_materials',
        'ranking_criteria': {
          'property_match': 0.5,
          'synthesis_feasibility': 0.3,
          'cost': 0.2
        },
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.ranking_result',
    });
    
    // 実験計画ステート
    const experimentPlanning = new tasks.LambdaInvoke(this, 'ExperimentPlanning', {
      lambdaFunction: experimentPlanningLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'create_experiment_plan',
        'session_id.$': '$.session_id',
        'materials.$': '$.ranking_result.Payload.ranked_materials',
        'target_properties.$': '$.property_target_result.Payload.target_properties',
        'available_equipment': [
          'UV-Vis Spectrometer',
          'Hall Effect Measurement System',
          'Laser Flash Analyzer',
          'X-ray Diffractometer',
          'Scanning Electron Microscope'
        ],
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.experiment_plan_result',
    });
    
    // リソース見積もりステート
    const estimateResources = new tasks.LambdaInvoke(this, 'EstimateResources', {
      lambdaFunction: experimentPlanningLambda,
      payload: sfn.TaskInput.fromObject({
        'process_type': 'estimate_resources',
        'session_id.$': '$.session_id',
        'experiment_plan.$': '$.experiment_plan_result.Payload.experiment_plan',
        'timestamp.$': '$.timestamp'
      }),
      resultPath: '$.resource_estimate_result',
    });
    
    // レポート生成ステート
    const generateReport = new sfn.Pass(this, 'GenerateReport', {
      parameters: {
        'status': 'completed',
        'session_id.$': '$.session_id',
        'requirements.$': '$.requirements',
        'target_properties.$': '$.property_target_result.Payload.target_properties',
        'candidate_materials.$': '$.inverse_design_result.Payload.candidate_materials',
        'ranked_materials.$': '$.ranking_result.Payload.ranked_materials',
        'experiment_plan.$': '$.experiment_plan_result.Payload.experiment_plan',
        'resource_estimate.$': '$.resource_estimate_result.Payload.resource_estimate',
        'completion_time.$': '$$.State.EnteredTime'
      },
      resultPath: '$.final_report',
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
    initialize.next(propertyTargetSetting);
    propertyTargetSetting.next(materialInverseDesign);
    materialInverseDesign.next(rankCandidates);
    rankCandidates.next(experimentPlanning);
    experimentPlanning.next(estimateResources);
    estimateResources.next(generateReport);
    generateReport.next(success);
    handleError.next(fail);
    
    // エラーキャッチ
    propertyTargetSetting.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    materialInverseDesign.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    rankCandidates.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    experimentPlanning.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    estimateResources.addCatch(handleError, {
      errors: ['States.ALL'],
      resultPath: '$.error',
    });
    
    // ステートマシンを作成
    this.stateMachine = new sfn.StateMachine(this, 'MaterialsWorkflow', {
      stateMachineName: `${projectName}-${envName}-materials-workflow`,
      definitionBody: sfn.DefinitionBody.fromChainable(initialize),
      role: stateMachineRole,
      timeout: cdk.Duration.hours(24),
      tracingEnabled: true,
      logs: {
        destination: new logs.LogGroup(this, 'StateMachineLogs', {
          logGroupName: `/aws/states/${projectName}-${envName}-materials-workflow`,
          removalPolicy: cdk.RemovalPolicy.DESTROY,
        }),
        level: sfn.LogLevel.ALL,
      },
    });
  }
}
