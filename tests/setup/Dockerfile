# Linux container for testing setup/install.sh offline, with downloads faked.
FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates curl git make tar unzip zip \
 && rm -rf /var/lib/apt/lists/* \
 && git config --system user.email "fixtures@example.com" \
 && git config --system user.name "Fixture Builder" \
 && git config --system init.defaultBranch main
