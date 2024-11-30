FROM quay.io/skopeo/stable

ENV SUMMARY="Image which allows using skopeo in AWS Batch." \
    DESCRIPTION="Image which allows using skopeo in AWS Batch." \
    NAME=aws-batch-skopeo

LABEL summary="$SUMMARY" \
      description="$DESCRIPTION" \
      io.k8s.description="$DESCRIPTION" \
      io.k8s.display-name="AWS Batch with Podman" \
      com.redhat.component="$NAME" \
      name="$FGC/$NAME" \
      version="$VERSION" \
      usage="This image can be used inside AWS Batch to perform container inspection and copies." \
      maintainer="Stephen Cuppett <steve@cuppett.com>" \
      org.opencontainers.image.source="https://github.com/cuppett/aws-ecr-mirror"

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