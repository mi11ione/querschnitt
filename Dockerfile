# Querschnitt service image: API + app + nightly delta (no GPU, no model weights; Apertus is an OpenAI-compatible endpoint
# set at run time via QS_BASE_URL / QS_API_KEY). One image for both compose profiles.
#   docker build -t querschnitt .
#   docker run --rm -p 127.0.0.1:8000:8000 querschnitt            (SQLite in /app/state, shipped data loaded on first start)
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src QS_DB=/app/state/querschnitt.sqlite QS_HOST=0.0.0.0 QS_PORT=8000 \
    QS_EXPORT_DIR=/app/data/opd QS_INPUTS=/app/data/inputs.jsonl.gz QS_RUN_DIR=/app/runs/main
WORKDIR /app
# dependencies from pyproject.toml (runtime + Postgres extra), cached apart from the code
COPY pyproject.toml /app/pyproject.toml
RUN python -c "import tomllib; p = tomllib.load(open('/app/pyproject.toml', 'rb'))['project']; \
print('\n'.join(p['dependencies'] + p['optional-dependencies']['pg']))" > /tmp/req.txt \
 && pip install -r /tmp/req.txt && rm /tmp/req.txt \
 && useradd --create-home --uid 10001 app
COPY --chown=app:app . /app
RUN mkdir -p /app/state /app/data /app/runs \
 && chown -R app:app /app/state /app/data /app/runs /app/src/querschnitt/schemes/adhoc
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1
CMD ["sh", "-c", "python -m querschnitt load --auto --if-empty && exec python -m querschnitt serve"]
