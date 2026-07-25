# Zero-dependency by design: the harness is standard-library only, so the Actor needs no
# pip install and no SDK — it talks to the Apify REST API with urllib. Smaller image,
# nothing to drift, and the same code runs locally with no Apify at all.
FROM python:3.11-slim

WORKDIR /usr/src/app
COPY . ./

ENV PYTHONUNBUFFERED=1
CMD ["python3", "-m", "actor_main"]
