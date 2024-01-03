import boto3
import os

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['TABLE_NAME']

def lambda_handler(event, context):

    http_method = event['httpMethod']
    path = event['resource']

    if http_method == 'GET':
        if path.endswith('/data'):
            return handle_get_data_request(event)
        else:
            return handle_get_request(event)
    else:
        return {
            'statusCode': 400,
            'body': 'Invalid request method'
        }

def handle_get_request(event):
    with open('template.html', 'r') as file:
        html_content = file.read()

    return {
        'statusCode': 200,
        'body': html_content,
        'headers': {
            'Content-Type': 'text/html',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        }
    }

def handle_get_data_request(event):
    unique_id = event['pathParameters']['id']
    
    table = dynamodb.Table(table_name)
    response = table.get_item(
        Key={
            'url': unique_id
        }
    )

    item = response.get('Item', None)
    if item is not None:
        table.delete_item(
            Key={
                'url': unique_id
            }
        )
        
    if item:
        result = {
            'statusCode': 200,
            'body': item['text'],
            'headers': {
                'Content-Type': 'text/plain',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }
    else:
        result = {
            'statusCode': 404,
            'body': 'Item not found',
            'headers': {
                'Content-Type': 'text/plain',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            }
        }

    return result
