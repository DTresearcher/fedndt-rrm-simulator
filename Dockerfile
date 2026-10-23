# Reproducible environment for the FNDT simulator.
FROM python:3.12.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/fndt src/fndt
COPY configs/scenarios configs/scenarios
COPY tests tests
COPY docs docs
COPY run.sh .
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
ENTRYPOINT ["bash", "run.sh"]
