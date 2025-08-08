FROM ubuntu:24.04
RUN apt-get update -y \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends \
          iputils-ping \
          curl \
          iproute2 \
          net-tools \
          dnsutils \
          nftables \
          ca-certificates \
    && rm -rf /var/lib/apt/lists/*