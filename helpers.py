import os
import subprocess

import boto3


def seed_auth():
    client = boto3.client('ssm')
    auth = client.get_parameter(
        Name=os.getenv('CONTAINER_AUTH_PARAMETER'),
        WithDecryption=True
    )

    f = open("/tmp/auth.json", "w")
    f.write(auth["Parameter"]["Value"])
    f.close()
