# The Python service of conditions B and C: numpy, scipy, sgp4. No GMAT, no gmat-mcp core, no network at run time.
FROM python:3.12-slim
RUN pip install --no-cache-dir --disable-pip-version-check numpy==2.5.4 scipy==1.18.1 sgp4==2.27
USER nobody
WORKDIR /tmp
CMD ["tail", "-f", "/dev/null"]
