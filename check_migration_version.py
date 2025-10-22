from app.db.base import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text('SELECT version_num FROM alembic_version'))
    version = result.fetchone()
    if version:
        print(f'Current DB version: {version[0]}')
    else:
        print('No version in database')

