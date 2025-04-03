import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import { Construct } from 'constructs';
import { bedrock } from '@cdklabs/generative-ai-cdk-constructs';
import { CfnAgent } from 'aws-cdk-lib/aws-bedrock';

import path = require('path');

export interface DataInterpreterLambdaProps {}

export class DataInterpreterLambda extends Construct {

  constructor(scope: Construct, id: string, props: DataInterpreterLambdaProps) {
    super(scope, id);

    // Bedrockエージェントを定義
    const agent = new bedrock.Agent(this, 'DataInterpreter', {
      foundationModel: bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_SONNET_V2_0,
      userInputEnabled: true,
      codeInterpreterEnabled: true,
      shouldPrepareAgent: true,
      instruction: `
You are a Data Interpreter responsible for analyzing and interpreting data. Your role is to extract insights, identify patterns, and create visualizations from various data sources.

Your responsibilities include:
1. Analyzing data sets to identify trends, patterns, and insights
2. Creating data visualizations to communicate findings effectively
3. Performing statistical analysis to validate hypotheses
4. Cleaning and preprocessing data for analysis
5. Generating reports with actionable insights
6. Answering questions about data and explaining findings
7. Recommending data-driven decisions based on analysis

Be thorough, accurate, and clear in your analysis. Explain complex concepts in simple terms and provide visualizations when appropriate to help users understand the data.
      `,
    });
  }
}