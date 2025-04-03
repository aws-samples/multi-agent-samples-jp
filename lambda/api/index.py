import json
import os
import boto3
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

# ロガーの設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS クライアントの初期化
sqs = boto3.client('sqs')
events = boto3.client('events')
stepfunctions = boto3.client('stepfunctions')

# 環境変数
ENV_NAME = os.environ.get('ENV_NAME', 'dev')
PROJECT_NAME = os.environ.get('PROJECT_NAME', 'smajp')
COMMUNICATION_QUEUE_URL = os.environ.get('COMMUNICATION_QUEUE_URL')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME')
STATE_MACHINE_ARN = os.environ.get('STATE_MACHINE_ARN')
ACCOUNT_ID = os.environ.get('ACCOUNT_ID')

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    API Gateway Lambda関数のハンドラー
    
    Args:
        event: Lambda関数のイベントデータ
        context: Lambda関数のコンテキスト
        
    Returns:
        APIレスポンス
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # HTTPメソッドとパスの取得
        http_method = event.get('httpMethod')
        path = event.get('path', '')
        
        # リクエストボディの解析
        body = {}
        if event.get('body'):
            body = json.loads(event.get('body'))
        
        # パスパラメータの取得
        path_parameters = event.get('pathParameters', {}) or {}
        
        # クエリパラメータの取得
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        # ユーザー情報の取得
        user_info = get_user_info(event)
        
        # ルーティング
        if path.startswith('/agents'):
            return handle_agents_route(http_method, path_parameters, query_parameters, body, user_info)
        elif path.startswith('/tasks'):
            return handle_tasks_route(http_method, path_parameters, query_parameters, body, user_info)
        else:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not Found'})
            }
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def get_user_info(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    リクエストからユーザー情報を取得
    
    Args:
        event: Lambda関数のイベントデータ
        
    Returns:
        ユーザー情報
    """
    # 認証は削除されたため、デフォルトのユーザー情報を返す
    return {
        'user_id': 'default-user',
        'email': 'default@example.com',
        'name': 'Default User'
    }

def handle_agents_route(http_method: str, path_parameters: Dict[str, str], 
                       query_parameters: Dict[str, str], body: Dict[str, Any],
                       user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    /agents エンドポイントのハンドラー
    
    Args:
        http_method: HTTPメソッド
        path_parameters: パスパラメータ
        query_parameters: クエリパラメータ
        body: リクエストボディ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    agent_id = path_parameters.get('agentId')
    
    if http_method == 'GET':
        if agent_id:
            # 特定のエージェント情報を取得
            return get_agent(agent_id, user_info)
        else:
            # エージェント一覧を取得
            return list_agents(query_parameters, user_info)
    elif http_method == 'POST':
        # 新しいエージェントを作成
        return create_agent(body, user_info)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

def handle_tasks_route(http_method: str, path_parameters: Dict[str, str], 
                      query_parameters: Dict[str, str], body: Dict[str, Any],
                      user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    /tasks エンドポイントのハンドラー
    
    Args:
        http_method: HTTPメソッド
        path_parameters: パスパラメータ
        query_parameters: クエリパラメータ
        body: リクエストボディ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    task_id = path_parameters.get('taskId')
    
    if http_method == 'GET':
        if task_id:
            # 特定のタスク情報を取得
            return get_task(task_id, user_info)
        else:
            # タスク一覧を取得
            return list_tasks(query_parameters, user_info)
    elif http_method == 'POST':
        # 新しいタスクを作成
        return create_task(body, user_info)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps({'error': 'Method Not Allowed'})
        }

def get_agent(agent_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    特定のエージェント情報を取得
    
    Args:
        agent_id: エージェントID
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    # ここでは簡略化のためにモックデータを返す
    # 実際の実装ではDynamoDBなどからデータを取得する
    agent = {
        'agent_id': agent_id,
        'agent_type': 'product_manager',
        'status': 'active',
        'created_at': '2023-01-01T00:00:00Z',
        'owner': user_info['user_id']
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(agent)
    }

def list_agents(query_parameters: Dict[str, str], user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    エージェント一覧を取得
    
    Args:
        query_parameters: クエリパラメータ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    # ここでは簡略化のためにモックデータを返す
    agents = [
        {
            'agent_id': 'agent-001',
            'agent_type': 'product_manager',
            'status': 'active',
            'created_at': '2023-01-01T00:00:00Z',
            'owner': user_info['user_id']
        },
        {
            'agent_id': 'agent-002',
            'agent_type': 'architect',
            'status': 'active',
            'created_at': '2023-01-02T00:00:00Z',
            'owner': user_info['user_id']
        }
    ]
    
    return {
        'statusCode': 200,
        'body': json.dumps(agents)
    }

def create_agent(body: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    新しいエージェントを作成
    
    Args:
        body: リクエストボディ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    agent_type = body.get('agent_type')
    
    if not agent_type:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'agent_type is required'})
        }
    
    # 新しいエージェントIDを生成
    agent_id = f"{agent_type}-{str(uuid.uuid4())[:8]}"
    
    # イベントを発行
    try:
        events.put_events(
            Entries=[
                {
                    'Source': 'api.agents',
                    'DetailType': 'AgentCreated',
                    'Detail': json.dumps({
                        'agent_id': agent_id,
                        'agent_type': agent_type,
                        'user_id': user_info['user_id']
                    }),
                    'EventBusName': EVENT_BUS_NAME
                }
            ]
        )
    except Exception as e:
        logger.error(f"Error emitting event: {str(e)}")
    
    # 新しいエージェント情報を返す
    agent = {
        'agent_id': agent_id,
        'agent_type': agent_type,
        'status': 'initializing',
        'created_at': datetime.utcnow().isoformat(),
        'owner': user_info['user_id']
    }
    
    return {
        'statusCode': 201,
        'body': json.dumps(agent)
    }

def get_task(task_id: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    特定のタスク情報を取得
    
    Args:
        task_id: タスクID
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    # Step Functionsの実行状態を取得
    try:
        region = os.environ.get('AWS_REGION')
        execution_arn = f"arn:aws:states:{region}:{ACCOUNT_ID}:execution:{task_id}"
        response = stepfunctions.describe_execution(
            executionArn=execution_arn
        )
        
        task = {
            'task_id': task_id,
            'status': response['status'],
            'start_date': response['startDate'].isoformat(),
            'input': json.loads(response['input']),
        }
        
        if 'output' in response:
            task['output'] = json.loads(response['output'])
        
        return {
            'statusCode': 200,
            'body': json.dumps(task)
        }
    except Exception as e:
        logger.error(f"Error getting task: {str(e)}")
        return {
            'statusCode': 404,
            'body': json.dumps({'error': 'Task not found'})
        }

def list_tasks(query_parameters: Dict[str, str], user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    タスク一覧を取得
    
    Args:
        query_parameters: クエリパラメータ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    # ここでは簡略化のためにモックデータを返す
    tasks = [
        {
            'task_id': 'task-001',
            'status': 'RUNNING',
            'start_date': '2023-01-01T00:00:00Z',
            'owner': user_info['user_id']
        },
        {
            'task_id': 'task-002',
            'status': 'SUCCEEDED',
            'start_date': '2023-01-02T00:00:00Z',
            'end_date': '2023-01-02T00:05:00Z',
            'owner': user_info['user_id']
        }
    ]
    
    return {
        'statusCode': 200,
        'body': json.dumps(tasks)
    }

def create_task(body: Dict[str, Any], user_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    新しいタスクを作成
    
    Args:
        body: リクエストボディ
        user_info: ユーザー情報
        
    Returns:
        APIレスポンス
    """
    requirement = body.get('requirement')
    task_type = body.get('task_type', 'development')
    
    if not requirement:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'requirement is required'})
        }
    
    # Step Functionsを実行
    try:
        # ワークフローに必要な入力形式に変換
        workflow_input = {
            'requirement': requirement,
            'task_type': task_type,
            'user_id': user_info['user_id']
        }
        
        logger.info(f"Starting workflow with input: {json.dumps(workflow_input)}")
        
        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps(workflow_input)
        )
        
        # 実行ARNからタスクIDを抽出
        execution_arn = response['executionArn']
        task_id = execution_arn.split(':')[-1]
        
        task = {
            'task_id': task_id,
            'requirement': requirement,
            'status': 'RUNNING',
            'start_date': response['startDate'].isoformat(),
            'owner': user_info['user_id']
        }
        
        return {
            'statusCode': 201,
            'body': json.dumps(task)
        }
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }