import boto3
from botocore.exceptions import BotoCoreError, ClientError

def lambda_handler(event, context):
    job_id = event['CodePipeline.job']['id']

    distribution_id = 'E3HUREUB4ETJKA'
    paths = ['/index.html', '/style.css', '/script.js']

    codepipeline = boto3.client('codepipeline')
    cloudfront = boto3.client('cloudfront')

    try:

        invalidation = cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(paths),
                    'Items': paths
                },
                'CallerReference': 'lambda-invalidation'
            }
        )

        codepipeline.put_job_success_result(jobId=job_id)
    except (BotoCoreError, ClientError) as e:
        print(e)
        codepipeline.put_job_failure_result(jobId=job_id, failureDetails={'message': str(e), 'type': 'JobFailed'})
