import boto3
from constructs import Construct
from aws_cdk import App, Stack, RemovalPolicy, Duration, CfnOutput, Fn
from aws_cdk import (
    aws_s3 as s3,
    aws_s3_assets as s3_assets,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_s3_deployment as s3deploy,
    aws_logs as logs
)

class CdkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        sts_client = boto3.client("sts")
        account = sts_client.get_caller_identity()["Account"]
    
        bucket = s3.Bucket(self, "S3Bucket",
            removal_policy=RemovalPolicy.DESTROY
        )
        bucket_name = bucket.bucket_name
        origin_access_identity = cloudfront.OriginAccessIdentity(self, "OriginAccessIdentity")

        CfnOutput(self, "BucketName",
            value=bucket_name,
            description="Resource bucket name",
            export_name="MyBucketName"
        )

        distribution = cloudfront.Distribution(self, "CloudFrontDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(bucket, origin_access_identity=origin_access_identity),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            default_root_object='index.html',
            price_class=cloudfront.PriceClass.PRICE_CLASS_100
        )
 
        bucket_policy = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["s3:GetObject"],
            resources=[bucket.bucket_arn+"/*"],
            principals=[iam.ServicePrincipal("cloudfront.amazonaws.com")],
            conditions={
                "StringEquals": {
                    "aws:SourceArn": f"arn:aws:cloudfront::{account}:distribution/{distribution.distribution_id}"
                }
            }
        )
        bucket.add_to_resource_policy(bucket_policy)

        asset = s3_assets.Asset(self, "Asset", path="../frontend_files")
        s3deploy.BucketDeployment(self, "DeployWebsite",
            sources=[s3deploy.Source.asset("../frontend_files")],
            destination_bucket=bucket,
            distribution=distribution,
            distribution_paths=["/*"]
        )
        bucket.add_to_resource_policy(iam.PolicyStatement(
            actions=["s3:GetObject"],
            resources=[bucket.bucket_arn+"/*"],
            principals=[iam.CanonicalUserPrincipal(origin_access_identity.cloud_front_origin_access_identity_s3_canonical_user_id)]
        ))

        secret_table = dynamodb.Table(self, "SecretTable",
            partition_key=dynamodb.Attribute(
                name="url",
                type=dynamodb.AttributeType.STRING
            ),
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="TTL"
        )

        give_secret_lambda = _lambda.Function(self, 'Give_secret',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='give_secret.lambda_handler',
            code=_lambda.Code.from_asset('../give_secret_lambda'), 
            memory_size=128,
            timeout=Duration.seconds(3),
            environment={
                "TABLE_NAME": secret_table.table_name
            }
        )
        logs.LogGroup(self, "GiveSecretLambdaLogGroup",
            log_group_name=f"/aws/lambda/{give_secret_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )

        api = apigw.RestApi(self, 'Api')

        get_secret_lambda = _lambda.Function(self, 'get_secret',
            runtime=_lambda.Runtime.PYTHON_3_8,
            handler='get_secret_give_link.lambda_handler',
            code=_lambda.Code.from_asset('../get_secret_lambda'),
            memory_size=128,
            timeout=Duration.seconds(3),
            environment={
                'BASE_URL': Fn.join("", ["https://", api.rest_api_id, ".execute-api.", self.region, ".amazonaws.com/prod/"]),
                "TABLE_NAME": secret_table.table_name
            }
        )
        logs.LogGroup(self, "GetSecretLambdaLogGroup",
            log_group_name=f"/aws/lambda/{get_secret_lambda.function_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY
        )


        root = api.root
        root.add_cors_preflight(
            allow_origins=['*'],
            allow_methods=['OPTIONS,POST'],
            allow_headers=['Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token']
        )

        integration_response = apigw.IntegrationResponse(
            status_code='200',
            response_parameters={
                'method.response.header.Access-Control-Allow-Origin': "'*'"
            },
            response_templates={
                'application/json': "$input.json('$')"
            }
        )

        method_response = apigw.MethodResponse(
            status_code='200',
            response_parameters={
                'method.response.header.Access-Control-Allow-Origin': True
            }
        )

        root.add_method('POST', apigw.LambdaIntegration(
            handler=get_secret_lambda,
            proxy=False,
            integration_responses=[integration_response]
        ), method_responses=[method_response])
        
        id_resource = root.add_resource('{id}')
        id_resource.add_method('GET', apigw.LambdaIntegration(
            handler=give_secret_lambda,
            proxy=True
        ), method_responses=[method_response])
        id_resource.add_cors_preflight(
            allow_origins=['*'],
            allow_methods=['OPTIONS,POST'],
            allow_headers=['Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token']
        )

        method_response = apigw.MethodResponse(
            status_code='200'
        )

        data_resource = id_resource.add_resource('data')

        data_resource.add_cors_preflight(
            allow_origins=['*'],
            allow_methods=['GET', 'OPTIONS'],
            allow_headers=['Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token']
        )

        data_resource.add_method('GET', apigw.LambdaIntegration(
            handler=give_secret_lambda,
            proxy=True
        ), method_responses=[method_response])


        get_secret_lambda.grant_invoke(iam.ServicePrincipal('apigateway.amazonaws.com'))
        give_secret_lambda.grant_invoke(iam.ServicePrincipal('apigateway.amazonaws.com'))

        secret_table.grant_read_write_data(get_secret_lambda)
        secret_table.grant_read_write_data(give_secret_lambda)
        

        api_url = api.url.rstrip("/")
        CfnOutput(self, "APIGatewayURL",
            value=api_url,
            description="API Gateway URL",
            export_name="MyAPIGatewayURL"
        )
        CfnOutput(self, "TableName",
            value=secret_table.table_name,
            description="DynamoDB table name",
            export_name="MyTableName"
        )
        CfnOutput(self, "CloudFrontDistributionID",
            value=distribution.distribution_id,
            description="CloudFront Distribution ID",
            export_name="MyCloudFrontDistributionID"
        )
        CfnOutput(self, "GiveSecretLambdaFunctionName",
            value=give_secret_lambda.function_name,
            description="Give Secret Lambda Function Name",
            export_name="MyGiveSecretLambdaFunctionName"
        )
        CfnOutput(self, "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="APP URL;CloudFront distribution URL, add A record to your domain if you want",
            export_name="MyCloudFrontURL"
        )
app = App()
CdkStack(app, "CdkStack")
app.synth()
