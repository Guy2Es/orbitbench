# The GMAT service of condition C: the gmat-worker image (GMAT R2026a, built from the public tarball) plus the
# gmat-mcp server at a pinned commit, run with the local backend. Build with docker/build_gmat.sh.
FROM gmat-worker:latest
USER root
RUN apt-get update && apt-get install -y --no-install-recommends python3-venv ca-certificates \
 && python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --disable-pip-version-check "mcp<2" "pydantic>=2.7" matplotlib plotly numpy sgp4 \
 && rm -rf /var/lib/apt/lists/*
COPY app/ /opt/app/
RUN mkdir -p /tmp/jobs && chown -R gmat /tmp/jobs /opt/app
USER gmat
WORKDIR /opt/app
ENTRYPOINT []
CMD ["tail", "-f", "/dev/null"]
