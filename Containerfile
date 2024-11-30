FROM quay.io/skopeo/stable

ENV SUMMARY="Image which allows using skopeo in AWS Batch to mirror ECR repositories." \
    DESCRIPTION="Image which allows using skopeo in AWS Batch to mirror ECR repositories." \
    NAME=aws-ecr-mirror

LABEL summary="$SUMMARY" \
      description="$DESCRIPTION" \
      io.k8s.description="$DESCRIPTION" \
      io.k8s.display-name="AWS Batch and ECR with skopeo" \
      name="$NAME" \
      version="stable" \
      usage="This image can be used inside AWS Batch to perform container inspection and copies." \
      maintainer="Stephen Cuppett steve@cuppett.com" \
      org.opencontainers.image.source="https://github.com/cuppett/aws-ecr-mirror" \
      org.opencontainers.image.url="ghcr.io/cuppett/aws-ecr-mirror" \
      org.opencontainers.image.documentation="https://github.com/cuppett/aws-ecr-mirror/blob/main/README.md"

# Installing OS support
RUN set -ex; \
    \
    dnf -y update; \
    dnf -y install \
        python3-pip \
    ; \
    dnf -y clean all; \
    rm -rf /var/cache/dnf

COPY requirements.txt controller.py mirror.py helpers.py ./
RUN pip install -r requirements.txt

ENTRYPOINT [""]