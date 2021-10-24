import boto3
import hashlib
import helpers
import subprocess
import sys

from boto3.dynamodb.conditions import Key

# Capture the logged in ECR repositories here (so we save some effort looping through)
logged_in = []
session = boto3.session.Session()
region = session.region_name
account_id = session.client("sts").get_caller_identity()["Account"]

def identify_targets(row: dict) -> list:
    # Accumulate the repositories and destinations involved.

    # Check Source first
    repositories = []
    if "dkr.ecr" in row["Source"]:
        repository = row["Source"][:row["Source"].index("/")]
        if repository not in logged_in:
            repositories.append(repository)

    # Accumulate the destinations
    destinations = []
    if "Destination" in row:
        print(row["Destination"])
        # Accumulate the destinations
        if type(row["Destination"]) is set:
            for dest in row["Destination"]:
                destinations.append(dest)
        else:
            for dest in row["Destination"].split(","):
                destinations.append(dest)

        # Accumulate the log-in sources
        for dest in destinations:
            if "dkr.ecr" in dest:
                repository = dest[:dest.index("/")]
                if repository not in repositories and repository not in logged_in:
                    repositories.append(repository)

    # Log in to everything we haven't
    for repo in repositories:
        rc = helpers.ecr_login(repo)
        if rc > 0:
            print("Failed logging in to: " + repo)
        else:
            logged_in.append(repo)

    # Check the tags
    source_result = subprocess.run(
        ["skopeo", "inspect", "--format", "'{{ .Digest }}'", "docker://" + row["Source"]],
        capture_output=True
    )
    print(source_result)
    source_digest = str(source_result.stdout)
    print("Source Digest: " + source_digest)
    to_remove = []
    for dest in destinations:
        dest_result = subprocess.run(
            ["skopeo", "inspect", "--format", "'{{ .Digest }}'", "docker://" + dest],
            capture_output=True
        )
        print(dest_result)
        dest_digest = str(dest_result.stdout)
        if dest_digest == source_digest:
            print("Unneeded " + dest)
            to_remove.append(dest)

    for remove in to_remove:
        destinations.remove(remove)

    return destinations


def submit_mirror_job(queue: str, definition: str, source: str, destinations: list):

    batch_client = boto3.client('batch')
    destination = ",".join(destinations)
    hashed_source = hashlib.sha1(source.encode()).hexdigest()
    resp = batch_client.submit_job(
        jobName=hashed_source,
        jobQueue=queue,
        jobDefinition=definition,
        parameters={
            'source': source,
            'dest': destination
        }
    )
    print("Submitted job for " + source + " to " + destination + ".")
    print(resp)


if __name__ == '__main__':
    if len(sys.argv) < 4 and len(sys.argv) != 6:
        print("Usage: controller.py mirror-table-name mirror_job_queue mirror_job_definition [repository tag]")
        exit(1)

    # Get the service resources/clients.
    dynamodb = boto3.resource('dynamodb')

    # Working it.
    table = dynamodb.Table(sys.argv[1])

    if len(sys.argv) == 6:
        repository = sys.argv[4]
        tag = sys.argv[5]
        key = account_id + ".dkr.ecr." + region + ".amazonaws.com/" + repository + ":" + tag
        print("Individual mirror request for: " + key)
        response = table.query(
            KeyConditionExpression=Key('Source').eq(key)
        )
        rows = response["Items"]
    else:
        response = table.scan()
        rows = response["Items"]

    # Iterate over the rows
    for item in rows:
        try:
            print("Evaluating mirror for: " + item["Source"])
            destination_list = identify_targets(item)

            # Submit the required batch jobs
            if len(destination_list) > 0:
                submit_mirror_job(sys.argv[2], sys.argv[3], item["Source"], destination_list)
            else:
                print("No mirroring required.")
        except:
            print("Insulating larger program. Exception occurred on this row.")

    exit(0)
