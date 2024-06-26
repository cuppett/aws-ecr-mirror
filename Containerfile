FROM registry.fedoraproject.org/fedora:40

ENV SUMMARY="Image which allows using skopeo in AWS Batch." \
    DESCRIPTION="Image which allows using skopeo in AWS Batch." \
    NAME=aws-batch-skopeo \
    VERSION=38

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
    dnf -y install \
        python3 \
        python3-pip \
        skopeo \
    ; \
    dnf -y clean all; \
    rm -rf /var/cache/dnf

# Preparing container tools support for non-systemd systems
RUN set -ex; \
    echo "[engine]" > /etc/containers/containers.conf; \
    echo "events_logger = \"file\"" >> /etc/containers/containers.conf;

COPY requirements.txt controller.py mirror.py helpers.py ./
RUN pip install -r requirements.txt
