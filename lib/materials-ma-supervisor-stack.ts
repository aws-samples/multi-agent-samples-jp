import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { MaterialsSupervisor } from './constructs/multi-agents/materials/materials-supervisor';

export interface MaterialsMaSvStackProps extends cdk.StackProps{
    envName: string;
    projectName: string;
    propertyTarget_alias: bedrock.AgentAlias,
    inverseDesign_alias: bedrock.AgentAlias,
    experimentPlanning_alias: bedrock.AgentAlias,
}

export class MaterialsMaSvStack extends cdk.Stack {
    constructor(scope: Construct, id: string, props: MaterialsMaSvStackProps) {
        super(scope, id, props);

        const { envName, projectName, propertyTarget_alias, inverseDesign_alias, experimentPlanning_alias } = props;

        const supervisorBase = new MaterialsSupervisor(this, 'MaterialsSupervisor', {
            envName: envName,
            projectName: projectName,
            propertyTarget_alias: propertyTarget_alias,
            inverseDesign_alias: inverseDesign_alias,
            experimentPlanning_alias: experimentPlanning_alias,
          })
    }
}
