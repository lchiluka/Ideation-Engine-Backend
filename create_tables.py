from db import engine, Base
import models  # ensure Concept is imported so Base.metadata knows about it

if __name__ == "__main__":
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
