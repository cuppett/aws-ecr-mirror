# Mirror Images in/out of AWS using ECR & Batch

This repository builds on the work started in [aws-codebuild-podman]. Using the plumbing from that project, 
we can build containers with [skopeo] capable of running in [AWS Batch][batch] to mirror images in and out
of our ECR repositories.

Using the below technologies, we'll automate mirroring images into and out of the 
AWS cloud:

| AWS service          | Description
|----------------------|------------
| [Batch][batch]       | Managed, batch environment. This is perfect for highly-parallel and/or long-running jobs.      
| [ECR][ecr]           | Managed container image repository.
| [Lambda][lambda]     | Functional execution in response to events. This can be custom events, but also events within the AWS cloud.
| [SQS][sqs]           | Managed queueing. Queue entries serve as jobs for AWS Batch and also as event sources for AWS Lambda.
| [DynamoDB][dynamodb] | Scalable NoSQL storage for easy key/value storage and retrieval across many AWS services and APIs.

This repository provides the templates and descriptions needed to provision container image repositories
and the build jobs needed to use [skopeo] in AWS Batch.

## Capabilities

- [x] Create all required resources with [CloudFormation][cloudformation]
- [x] Mirror changed images into AWS periodically
- [x] Mirror changed images within AWS based on ECR CloudWatch Event Rule trigger
- [ ] Mirror changed images to external repositories on push

> Note: For ECR<->ECR replication, you should use the built-in [ECR private replication][ecr-replication] functionality.


## Intended Design

![Repository Stack Example](images/arch.png)

1. A CloudWatch timer of the user's choosing invokes AWS Batch (controller.py)
2. -or- A CloudWatch event on ECR image changes invokes AWS Batch (controller.py)
3. The control batch job queries the DynamoDB table
   1. Identify if the SHAs still match from source/target
   2. If not, submit a copy/mirror job (mirror.py)
4. The mirror jobs run a `skopeo copy --all` from src->dest

### Mirror Table Definition

The core of the mirror table is a source and destination. Destination can be individual strings,
comma-separated strings or a string list.

| Source                              | Destination
|-------------------------------------|------------
| docker.io/library/golang:1.17       | 0123456789.dkr.ecr.us-east-1.amazonaws.com/golang:1.17<br>0123456789.dkr.ecr.us-east-1.amazonaws.com/golang:latest
| docker.io/library/postgres:14       | 0123456789.dkr.ecr.us-east-1.amazonaws.com/postgres:14,0123456789.dkr.ecr.us-east-1.amazonaws.com/postgres:latest
| registry.fedoraproject.org/fedora:34| 0123456789.dkr.ecr.us-east-1.amazonaws.com/fedora:34

## Pre-requisites

- [aws-codebuild-podman] tools & resources configured and available in your account

## Costs

AWS costs are charged by resource usage and time. These stacks will provide a best-effort
tear down of the resources consumed when stacks are deleted. To help identify items 
in your account which may lead to items on your bill, here is a helpful checklist
(in addition to those from [aws-codebuild-podman]:

- [DynamoDB pricing][dynamodb-pricing]
- [Lambda pricing][lambda-pricing]

## Running a Mirror Job Ad-Hoc

The mirror.py has the following syntax:

```
python mirror.py src dest1 [dest2 [... destN]]
```

The ```dest``` parameters can be either space or comma-separated. 

Example:

```commandline
python mirror.py registry.fedoraproject.org/fedora:34 \
  0123456789.dkr.ecr.us-east-1.amazonaws.com/fedora:34,0123456789.dkr.ecr.us-east-1.amazonaws.com/fedora:latest \ 
  0123456789.dkr.ecr.us-east-2.amazonaws.com/fedora:34 0123456789.dkr.ecr.us-east-2.amazonaws.com/fedora:latest
```

The above will copy the public fedora:34 image to four separate location/tags. 

### Submitting to AWS Batch

Now that we have a job environment and queues for these things, we can easily submit jobs independently of the system
and have the cloud mirror in images on our behalf.

```commandline
aws batch --region us-east-1 submit-job \
  --job-name test \
  --job-queue MirrorQueue-4b9b16a4f56c734 \  
  --job-definition MirrorJob-6cc6ca701f705b0 \  
  --parameters source=registry.fedoraproject.org/fedora:34,dest=0123456789.dkr.ecr.us-east-1.amazonaws.com/fedora:34
{
    "jobArn": "arn:aws:batch:us-east-1:0123456789:job/28399b82-5a54-4650-a697-6666501a360a",
    "jobName": "test",
    "jobId": "28399b82-5a54-4650-a697-6666501a360a"
}
```

Using the JSON format of the [CLI command][cli-submit-job] will allow you to submit a comma-separated list of 
destinations.


[aws-codebuild-podman]: https://github.com/cuppett/aws-codebuild-podman
[cli-submit-job]: https://docs.aws.amazon.com/cli/latest/reference/batch/submit-job.html
[cloudformation]: https://aws.amazon.com/cloudformation/
[batch]: https://aws.amazon.com/batch/
[dynamodb]: https://aws.amazon.com/dynamodb/
[dynamodb-pricing]: https://aws.amazon.com/dynamodb/pricing/
[ecr]: https://aws.amazon.com/ecr/
[ecr-replication]: https://docs.aws.amazon.com/AmazonECR/latest/userguide/replication.html
[lambda]: https://aws.amazon.com/lambda/
[lambda-pricing]: https://aws.amazon.com/lambda/pricing/
[sqs]: https://aws.amazon.com/sqs/
[skopeo]: https://github.com/containers/skopeo
