# Burner Link

Share messages via URLs that expire after a single view or 24 hours.

Deploy to AWS with CDK, free tier eligible.

## Prerequisites

- [AWS CLI latest](https://aws.amazon.com/cli/): You should also have an AWS account set up with permissions to deploy services.
- [CDK 2.0 or later](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html)
- [NodeJS 14.15.0 or later](https://nodejs.org/en/download/) npm install -g aws-cdk
- [Python 3.10](https://www.python.org/downloads/) 

## Setup

```bash
# Clone the repository
git clone {this repo}

# Navigate into the repository
cd {this repo}/CDK

# Set your AWS profile
export AWS_PROFILE=cdk

# Set your AWS region
export AWS_DEFAULT_REGION=yourregion

# Create a Python virtual environment
python -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Deploy the CDK stack
cdk deploy --outputs-file outputs.json

# Run the post-deployment script
python post_deploy.py
```

Voilà!
Visit the `BurnerLink.CloudFrontURL` in the `outputs.json` file to use the service.
