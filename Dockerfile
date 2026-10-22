# Reproducible environment for the FNDT simulator v2.
FROM python:3.12.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 MPLBACKEND=Agg
WORKDIR /app
COPY requirements-v2.txt .
RUN pip install --no-cache-dir -r requirements-v2.txt
COPY src/fndt src/fndt
COPY configs/v2 configs/v2
COPY tests_v2 tests_v2
COPY docs/v2 docs/v2
COPY run_v2.sh .
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
ENTRYPOINT ["bash", "run_v2.sh"]
