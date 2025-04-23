#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { BizDevMaStack } from '../lib/bizdev-ma-agent-stack';
import { BizDevWorkflowStack } from '../lib/bizdev-wf-stack';
import { CFnAnalysisEventDrivenStack } from '../lib/cfnfa-ed-stack';
import { MaterialsWorkflowStack } from '../lib/materials-workflow-stack';
import { MaterialsMaSvStack } from '../lib/materials-ma-supervisor-stack';
import { Aspects, IAspect } from 'aws-cdk-lib';
import { AwsSolutionsChecks, NagSuppressions } from 'cdk-nag';
import { IConstruct } from 'constructs';
import { BizDevMaSvStack } from '../lib/bizdev-ma-supervisor-stack';

const app = new cdk.App();

// CDK Nagを適用
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }));

// 環境変数から環境名を取得（デフォルトは 'dev'）
const envName = process.env.ENV_NAME || 'dev';

// 環境変数からリージョンとアカウントを取得、または CLI の設定を使用
const env = { 
  account: process.env.CDK_DEFAULT_ACCOUNT || process.env.AWS_ACCOUNT_ID, 
  region: process.env.CDK_DEFAULT_REGION || process.env.AWS_REGION || 'us-west-2'
};

// プロジェクト名のプレフィックス
const projectName = 'masjp';

// 通知メールアドレス（環境変数から取得）
const notificationEmail = process.env.NOTIFICATION_EMAIL;

// 事業開発マルチエージェント（コラボレーター）
const bizDevMultiagentStack = new BizDevMaStack(app, `${projectName}-bizdev-ma-agent-${envName}`, {
  env,
  envName,
  projectName,
  notificationEmail,
});

// 事業開発マルチエージェント（スーパーバイザー）
const bizDevSupervisorStack = new BizDevMaSvStack(app, `${projectName}-bizdev-ma-sv-${envName}`, {
  env,
  envName,
  projectName,
  pdm_alias: bizDevMultiagentStack.pdm_alias,
  architect_alias: bizDevMultiagentStack.architect_alias,
  engineer_alias: bizDevMultiagentStack.engineer_alias,
});

// 事業開発エージェントワークフロー
const bizDevWorkflow = new BizDevWorkflowStack(app, `${projectName}-bizdev-wf-${envName}`, {
  env,
  envName,
  projectName,
  notificationEmail,
});

// CFn分析 イベント駆動エージェント
const cfnFailureAnalysis = new CFnAnalysisEventDrivenStack(app, `${projectName}-cfnfa-ed-${envName}`, {
  env,
  envName,
  projectName,
  notificationEmail,
});

// マテリアルインフォマティクスワークフロー
const materialsWorkflow = new MaterialsWorkflowStack(app, `${projectName}-materials-wf-${envName}`, {
  env,
  envName,
  projectName,
});

// マテリアルインフォマティクスマルチエージェント（スーパーバイザー）
const materialsSupervisor = new MaterialsMaSvStack(app, `${projectName}-materials-ma-sv-${envName}`, {
  env,
  envName,
  projectName,
  propertyTarget_alias: materialsWorkflow.propertyTargetAlias,
  inverseDesign_alias: materialsWorkflow.inverseDesignAlias,
  experimentPlanning_alias: materialsWorkflow.experimentPlanningAlias,
});

// マルチエージェントのスーパーバイザー、コラボレーターの明示的な依存関係の定義
bizDevSupervisorStack.addDependency(bizDevMultiagentStack)
materialsSupervisor.addDependency(materialsWorkflow)

// CDK Nagの警告を抑制（一箇所に集約）
const commonSuppressions = [
  { id: 'AwsSolutions-IAM5', reason: 'サンプル環境のため、移植性・追従性向上のためにワイルドカードを導入している。本番環境では適切に制限される必要があります' },
  // { id: 'AwsSolutions-L1', reason: 'Lambda関数は最新のPythonランタイムを使用しています' },
];

// 各スタックに共通の抑制設定を適用
NagSuppressions.addStackSuppressions(bizDevMultiagentStack, commonSuppressions);
NagSuppressions.addStackSuppressions(bizDevSupervisorStack, commonSuppressions);
NagSuppressions.addStackSuppressions(bizDevWorkflow, commonSuppressions);
NagSuppressions.addStackSuppressions(cfnFailureAnalysis, commonSuppressions);
NagSuppressions.addStackSuppressions(materialsWorkflow, commonSuppressions);
NagSuppressions.addStackSuppressions(materialsSupervisor, commonSuppressions);
