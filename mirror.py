import base64
import boto3
import string
import subprocess
import sys

from helpers import seed_auth


def aws_login(ecr, ecr_repository: string) -> int:
    """Logs into AWS ECR using the provided password.
    The boto client library is toggled before calling this function and then used to fetch the authorization token
    which is then decoded and passed to skopeo login.
    """
    # Logging into the repository
    auth_token = ecr.get_authorization_token()

    if auth_token is None or \
            len(auth_token["authorizationData"]) == 0:
        print("Failure fetching authorization data.")
        return 2

    try:
        auth_data = auth_token["authorizationData"][0]
    except KeyError:
        auth_data = auth_token["authorizationData"]

    if "authorizationToken" not in auth_data:
        print("Failure finding authorization token.")
        return 3

    # The authorizationToken is a base64 encoded version of 'AWS:my_password_here'
    auth_password = base64.b64decode(auth_data["authorizationToken"])[4:]

    logging_in = \
        subprocess.run(
            ["skopeo", "login", "--authfile=/tmp/auth.json", "-u", "AWS", "--password-stdin", ecr_repository],
            input=auth_password,
            stderr=subprocess.STDOUT,
        )

    if logging_in.returncode != 0:
        print("Failure logging in to " + ecr_repository)
    return logging_in.returncode

def ecr_login(repo: string) -> int:
    repo_parts = repo.split(".")
    ecr = boto3.client("ecr", region_name=repo_parts[3])
    return aws_login(ecr, repo)

def ecr_public_login(repo: string) -> int:
    ecr = boto3.client("ecr-public")
    return aws_login(ecr, repo)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: mirror.py source dest1 [dest2 [... destN]]")
        exit(1)

    seed_auth()

    # Maintain unique list
    repositories = []
    for reference in sys.argv[1:]:
        for x in reference.split(","):
            # Identified this is an AWS target location
            if "dkr.ecr" in x:
                # Removing off the repository and tag info
                repository = x[:x.index("/")]
                # Check against unique hostname list
                if repository not in repositories:
                    # Login in uniquely
                    repositories.append(repository)
                    rc = ecr_login(repository)
                    if rc > 0:
                        exit(rc)
            elif "public.ecr" in x:
                # Split the string into a list of substrings using '/' as a delimiter
                substrings = x.split('/')
                # The first substring is the hostname, the second is the account
                # The third is the repository, which we don't need
                repository = "/".join(substrings[:2])

                # Check against unique hostname list
                if repository not in repositories:
                    # Login in uniquely
                    repositories.append(repository)
                    rc = ecr_public_login(repository)
                    if rc > 0:
                        exit(rc)

    for dest in sys.argv[2:]:
        for x in dest.split(","):
            # Run skopeo copy for each destination listed.
            copy_result = subprocess.run(
                ["skopeo", "copy", "--authfile", "/tmp/auth.json", "--retry-times", "5", "--all", "docker://" + sys.argv[1], "docker://" + x],
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
            )
            if copy_result.returncode > 0:
                exit(copy_result.returncode)

    exit(0)
