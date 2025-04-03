import json
import boto3
import os
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # イベントからスタック情報を取得
        stack_id = event.get('detail', {}).get('stack-id', '')
        stack_name = event.get('detail', {}).get('stack-name', '')
        status = event.get('detail', {}).get('status', '')
        status_reason = event.get('detail', {}).get('status-reason', '')
        logical_resource_id = event.get('detail', {}).get('logical-resource-id', '')
        resource_type = event.get('detail', {}).get('resource-type', '')
        template_body = None
        
        # スタック情報が不足している場合は、CloudFormation APIから取得を試みる
        if stack_id:
            try:
                cfn = boto3.client('cloudformation')
                
                # スタックの詳細情報を取得
                stack_response = cfn.describe_stacks(StackName=stack_id)
                if stack_response and 'Stacks' in stack_response and len(stack_response['Stacks']) > 0:
                    stack = stack_response['Stacks'][0]
                    stack_name = stack.get('StackName', stack_name)
                
                # 必ずCloudFormationテンプレートを取得する
                try:
                    template_response = cfn.get_template(
                        StackName=stack_id,
                        TemplateStage='Processed'  # 処理済みのテンプレートを取得
                    )
                    if template_response and 'TemplateBody' in template_response:
                        template_body = template_response['TemplateBody']
                        logger.info(f"Successfully retrieved template for stack {stack_name}")
                    else:
                        logger.warning(f"Template body not found in response for stack {stack_name}")
                except Exception as template_error:
                    logger.error(f"Error retrieving template: {str(template_error)}")
                    # テンプレート取得に失敗しても処理を続行
                
                # スタック情報が不足している場合のみ、イベント情報を取得
                if not stack_name or not logical_resource_id or not resource_type:
                    # スタックイベントから失敗したリソースの情報を取得
                    events_response = cfn.describe_stack_events(StackName=stack_id)
                    if events_response and 'StackEvents' in events_response:
                        # 失敗したリソースを探す
                        for event in events_response['StackEvents']:
                            if event.get('ResourceStatus') in ['CREATE_FAILED', 'UPDATE_FAILED', 'DELETE_FAILED']:
                                logical_resource_id = event.get('LogicalResourceId', logical_resource_id)
                                resource_type = event.get('ResourceType', resource_type)
                                status_reason = event.get('ResourceStatusReason', status_reason)
                                break
            except Exception as e:
                logger.error(f"Error retrieving stack details: {str(e)}")
                return {
                    'error': str(e),
                    'stackId': stack_id,
                    'stackName': stack_name,
                    'timestamp': datetime.now().isoformat()
                }
        
        # 解析結果を返す
        result = {
            'stackId': stack_id,
            'stackName': stack_name,
            'status': status,
            'statusReason': status_reason,
            'logicalResourceId': logical_resource_id,
            'resourceType': resource_type,
            'timestamp': datetime.now().isoformat()
        }
        
        # テンプレート情報を追加（サイズが大きい場合は考慮）
        if template_body:
            # テンプレートが大きすぎる場合は要約情報のみを含める
            if isinstance(template_body, str) and len(template_body) > 50000:
                result['templateSummary'] = "Template retrieved but too large to include in response"
                result['hasTemplate'] = True
                
                # テンプレートの主要な部分だけを抽出
                try:
                    template_json = json.loads(template_body) if isinstance(template_body, str) else template_body
                    resources_count = len(template_json.get('Resources', {}))
                    result['resourcesCount'] = resources_count
                    
                    # 失敗したリソースの定義だけを抽出
                    if logical_resource_id and logical_resource_id in template_json.get('Resources', {}):
                        result['failedResourceDefinition'] = template_json['Resources'][logical_resource_id]
                except Exception as e:
                    logger.warning(f"Could not parse template JSON: {str(e)}")
            else:
                result['template'] = template_body
        
        return result
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        return {
            'error': str(e),
            'stackId': event.get('detail', {}).get('stack-id', ''),
            'stackName': event.get('detail', {}).get('stack-name', ''),
            'timestamp': datetime.now().isoformat()
        }
