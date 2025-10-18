web: sh -c "echo '🔄 Running migrations...' && alembic upgrade head && echo '✅ Migrations complete' && echo '🚀 Starting FastAPI server...' && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"


