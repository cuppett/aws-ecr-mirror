from boto3.dynamodb.conditions import Key
from botocore.config import Config
from operator import itemgetter

import boto3
import hashlib
import subprocess
import sys
import traceback

from helpers import seed_auth

session = boto3.session.Session()
region = session.region_name
account_id = session.client("sts").get_caller_identity()["Account"]


def get_ecr_image_digest(image_url: str) -> str:
    hostname, image = itemgetter(0, 1)(image_url.split("/", 1))
    ecr_account, ecr_region = itemgetter(0, 3)(hostname.split("."))
    image_name, ecr_tag = itemgetter(0, 1)(image.split(":"))

    ecr_config = Config(
        region_name=ecr_region
    )
    ecr_client = boto3.client('ecr', config=ecr_config)

    ecr_image = ecr_client.describe_images(
        registryId=ecr_account,
        repositoryName=image_name,
        imageIds=[
            {
                'imageTag': ecr_tag
            },
        ]
    )
    print(ecr_image)
    if len(ecr_image['imageDetails']) > 0:
        return ecr_image['imageDetails'][0]['imageDigest'];
    else:
        return ""


def get_image_digest(image_url: str) -> str:
    if "dkr.ecr" in image_url:
        return get_ecr_image_digest(image_url)
    else:
        result = subprocess.run(
            ["skopeo", "--command-timeout", "10s", "inspect", "--authfile", "/tmp/auth.json", "--retry-times", "5", "--format", "'{{ .Digest }}'",
             "docker://" + image_url],
            capture_output=True
        )
        print(result)
        result_digest = result.stdout.decode('UTF-8').strip().strip("'")
        return result_digest


def identify_targets(row: dict) -> list:
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

    # Check the tags
    source_digest = get_image_digest(row["Source"])
    if len(source_digest) < 64:
        return []

    to_remove = []
    for dest in destinations:
        dest_digest = get_image_digest(dest)
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

    seed_auth()

    # Get the service resources/clients.
    dynamodb = boto3.resource('dynamodb')

    # Working it.
    table = dynamodb.Table(sys.argv[1])

    if len(sys.argv) == 6:
        repository = sys.argv[4]
        tag = sys.argv[5]
        key = account_id + ".dkr.ecr." + region + ".amazonaws.com/" + repository + ":" + tag
        print("Individual mirror request for: " + key)
        query_results = table.query(
            KeyConditionExpression=Key('Source').eq(key)
        )
        rows = query_results["Items"]
    else:
        scan_results = table.scan()
        rows = scan_results["Items"]

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
            print(traceback.format_exc())
            print(sys.exc_info()[2])

    exit(0)
