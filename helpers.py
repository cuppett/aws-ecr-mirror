import base64
import boto3
import string
import subprocess


def ecr_login(repo: string) -> int:
    repo_parts = repo.split(".")
    ecr = boto3.client("ecr", region_name=repo_parts[3])

    # Logging into the repository
    auth_token = ecr.get_authorization_token()
    if auth_token is None or \
            len(auth_token["authorizationData"]) == 0 or \
            "authorizationToken" not in auth_token["authorizationData"][0]:
        print("Failure fetching authorization token.")
        return 2
    # The authorizationToken is a base64 encoded version of 'AWS:my_password_here'
    auth_password = base64.b64decode(auth_token["authorizationData"][0]["authorizationToken"])[4:]

    logging_in = \
        subprocess.run(
            ["skopeo", "login", "-u", "AWS", "--password-stdin", repo],
            input=auth_password,
            stderr=subprocess.STDOUT,
        )

    if logging_in.returncode != 0:
        print("Failure logging in to " + repo)
    return logging_in.returncode
