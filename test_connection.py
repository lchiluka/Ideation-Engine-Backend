# test_connection.py

from db import engine
from dotenv import load_dotenv
import os
from sqlalchemy import text

load_dotenv()
print("URL:", os.getenv("DATABASE_URL"))

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Database connected:", result.scalar())
