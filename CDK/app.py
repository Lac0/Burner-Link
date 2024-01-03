#!/usr/bin/env python3
import os
import sys
import aws_cdk as cdk
sys.path.append('../IAC')
from appstack import CdkStack

app = cdk.App()
CdkStack(app, "BurnerLink")
app.synth()
