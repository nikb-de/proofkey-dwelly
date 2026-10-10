FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY tools/dwelly_cases /app/tools/dwelly_cases
COPY tools/dwelly_model /app/tools/dwelly_model
ENTRYPOINT ["python", "-B", "-m", "tools.dwelly_model"]
CMD ["--help"]
