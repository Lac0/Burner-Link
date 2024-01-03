import json
import uuid
import time
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['TABLE_NAME']
base_url = os.environ.get('BASE_URL')

def lambda_handler(event, context):
    input_text = event['text']
    unique_id = str(uuid.uuid4())
    current_time = int(time.time())
    ttl_time = current_time + 24*60*60  # 24 hours from now

    table = dynamodb.Table(table_name)
    table.put_item(
        Item={
            'url': unique_id,
            'text': input_text,
            'TTL': ttl_time
        }
    )

    one_time_url = f"{base_url}{unique_id}"

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'one_time_url': one_time_url
        }),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'OPTIONS,POST'
        }
    }

    return response
