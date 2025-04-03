import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { BizDevSupervisor } from './constructs/multi-agents/bizdev/bizdev-supervisor';

export interface BizDevMaSvStackProps extends cdk.StackProps{
    envName: string;
    projectName: string;
    pdm_alias: bedrock.AgentAlias,
    architect_alias: bedrock.AgentAlias,
    engineer_alias: bedrock.AgentAlias,
}

export class BizDevMaSvStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: BizDevMaSvStackProps) {
        super(scope, id, props);

        const { envName, projectName, pdm_alias, architect_alias, engineer_alias } = props;

        const supervisorBase = new BizDevSupervisor(this, 'BizDevSupervisor', {
            envName: envName,
            projectName: projectName,
            pdm_alias: pdm_alias,
            architect_alias: architect_alias,
            engineer_alias: engineer_alias,
          })
    }
}