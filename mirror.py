import base64
import boto3
import string
import subprocess
import sys


def ecr_login(repo: string) -> int:
    repo_parts = repository.split(".")
    ecr = boto3.client("ecr", region_name=repo_parts[3])

    # Logging into the repository
    auth_token = ecr.get_authorization_token()
    if auth_token is None or \
            len(auth_token["authorizationData"]) == 0 or \
            "authorizationToken" not in auth_token["authorizationData"][0]:
        print("Failure fetching authorzation token.")
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
        print("Failure logging in to " + repository)
    return logging_in.returncode


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: mirror.py source dest1 [dest2 [... destN]]")
        exit(1)

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

    for dest in sys.argv[2:]:
        for x in dest.split(","):
            # Run skopeo copy for each destination listed.
            copy_result = subprocess.run(
                ["skopeo", "copy", "--all", "docker://" + sys.argv[1], "docker://" + x],
                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL
            )
            if copy_result.returncode > 0:
                exit(copy_result.returncode)

    exit(0)
