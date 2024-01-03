import boto3
import json
import os
import zipfile
import time 

s3_client = boto3.client('s3')
lambda_client = boto3.client('lambda')
cloudfront_client = boto3.client('cloudfront')

def read_outputs(filename):
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"{filename} not found.")
        return None

def create_zip(zip_path):
    directory_path = "../give_secret_lambda"
    
    print(f"Creating zip from directory: {directory_path}")
    if not os.path.exists(directory_path):
        print(f"Directory {directory_path} does not exist.")
        return

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arc_path = os.path.relpath(file_path, directory_path)
                print(f"Adding {file_path} as {arc_path} to zip...")
                zipf.write(file_path, arc_path)

    print(f"Zip file created at {zip_path}")
        
def replace_placeholder(file_path, output_path, *args):
    with open(file_path, 'r', encoding='utf-8') as file:
        file_contents = file.read()

    for i in range(0, len(args), 2):
        placeholder = args[i]
        value = args[i+1]
        file_contents = file_contents.replace(placeholder, value)

    with open(output_path, 'w', encoding='utf-8') as file:
        file.write(file_contents)

def upload_file(bucket_name, file_path, object_name=None, content_type=None):
    if object_name is None:
        object_name = os.path.basename(file_path)
    extra_args = {}
    if content_type:
        extra_args['ContentType'] = content_type
    s3_client.upload_file(file_path, bucket_name, object_name, ExtraArgs=extra_args)


def update_lambda_code(function_name, zip_file_path):
    print(f"Updating function {function_name} with zip file {zip_file_path}")
    if not os.path.exists(zip_file_path):
        print(f"Zip file {zip_file_path} does not exist, creating...")
        create_zip(zip_file_path)
    with open(zip_file_path, 'rb') as file:
        zip_bytes = file.read()
    print(f"Updating function {function_name}...")
    lambda_client.update_function_code(
        FunctionName=function_name,
        ZipFile=zip_bytes
    )
    print(f"Function {function_name} updated.")

def invalidate_cloudfront(distribution_id, paths):
    cloudfront_client.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {
                'Quantity': len(paths),
                'Items': paths
            },
            'CallerReference': str(time.time())
        }
    )

def main():
    outputs = read_outputs('./outputs.json')['BurnerLink']

    bucket_name = outputs['BucketName']
    apigw_url = outputs['APIGatewayURL'].rstrip("/")
    cloudfront_url = outputs['CloudFrontURL']
    give_secret_lambda_name = outputs['GiveSecretLambdaFunctionName']
    print(outputs)
    frontend_files_path = "../frontend_files"
    give_secret_files_path = "../give_secret_lambda"

    replace_placeholder(
        os.path.join(frontend_files_path, "index.html.template"),
        os.path.join(frontend_files_path, "index.html"),
        "__CLOUDFRONT_URL__",
        cloudfront_url
    )
    replace_placeholder(
        os.path.join(frontend_files_path, "script.js.template"),
        os.path.join(frontend_files_path, "script.js"),
        "__APIGW_URL__",
        apigw_url
    )
    replace_placeholder(
        os.path.join(give_secret_files_path, "template.html.template"),
        os.path.join(give_secret_files_path, "template.html"),
        "__APIGW_URL__",
        apigw_url,
        "__CLOUDFRONT_URL__",
        cloudfront_url
    )
    update_lambda_code(give_secret_lambda_name, "../give_secret_lambda/give_secret_lambda.zip")

    upload_file(bucket_name, os.path.join(give_secret_files_path, "template.html"), "template.html")
    upload_file(bucket_name, os.path.join(frontend_files_path, "index.html"), content_type='text/html')
    upload_file(bucket_name, os.path.join(frontend_files_path, "script.js"), content_type='application/x-javascript')

    cloudfront_distribution_id = outputs['CloudFrontDistributionID']
    invalidate_cloudfront(cloudfront_distribution_id, ['/*'])

if __name__ == "__main__":
    main()
