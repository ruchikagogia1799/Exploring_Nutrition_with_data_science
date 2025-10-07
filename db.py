# db.py — handles all database interactions
import os
import bcrypt
import streamlit as st
from sqlalchemy import (
    create_engine, MetaData, Table, Column,
    Integer, String, Float, Text
)
from sqlalchemy.sql import select, or_, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# -----------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# -----------------------------------------------------
load_dotenv()

# Priority:
# 1️⃣ Streamlit Cloud Secrets
# 2️⃣ Local .env file
def get_env_var(name: str) -> str:
    try:
        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        pass
    return os.getenv(name)


# -----------------------------------------------------
# DATABASE CONNECTION
# -----------------------------------------------------
DATABASE_URL = get_env_var("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL is missing. Please set it in .env or Streamlit Secrets.")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()

# -----------------------------------------------------
# TABLE DEFINITION
# -----------------------------------------------------
users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True),
    Column("username", String, unique=True, nullable=False),
    Column("email", String, unique=True, nullable=False),
    Column("password", Text, nullable=False),
    Column("weight", Float),
    Column("height", Float),
    Column("age", Integer),
    Column("gender", String),
    Column("activity", String),
)

# -----------------------------------------------------
# AUTO-CREATE TABLE IF MISSING
# -----------------------------------------------------
with engine.begin() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            weight NUMERIC,
            height NUMERIC,
            age INT,
            gender TEXT,
            activity TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """))
metadata.create_all(engine)

Session = sessionmaker(bind=engine)

# -----------------------------------------------------
# HELPER FUNCTION
# -----------------------------------------------------
def _row_to_dict(row):
    """Convert SQLAlchemy Row to dict safely"""
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)

# -----------------------------------------------------
# CRUD FUNCTIONS
# -----------------------------------------------------
def user_exists(username, email):
    with Session() as ses:
        q = select(users).where(or_(
            users.c.username == username,
            users.c.email == email
        ))
        return ses.execute(q).fetchone() is not None


def register_user(username, email, password, weight=None, height=None, age=None, gender=None, activity=None):
    """Registers a new user with bcrypt password hashing"""
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    with Session() as ses:
        try:
            ses.execute(users.insert().values(
                username=username.strip(),
                email=email.strip(),
                password=hashed_pw,
                weight=weight,
                height=height,
                age=age,
                gender=gender,
                activity=activity
            ))
            ses.commit()
            return True
        except Exception as e:
            ses.rollback()
            print("❌ Error registering user:", e)
            return False


def login_user(identifier, password):
    """Login using username OR email"""
    with Session() as ses:
        q = select(users).where(or_(
            users.c.username.ilike(identifier.strip()),
            users.c.email.ilike(identifier.strip())
        ))
        row = ses.execute(q).fetchone()
        if not row:
            return None

        row = _row_to_dict(row)
        stored_pw = row.get("password")

        if stored_pw and bcrypt.checkpw(password.encode("utf-8"), stored_pw.encode("utf-8")):
            return row
        return None


def update_user(user_id, updates: dict):
    """Update user profile details"""
    with Session() as ses:
        try:
            ses.execute(users.update().where(users.c.id == user_id).values(**updates))
            ses.commit()
            return True
        except Exception as e:
            ses.rollback()
            print("❌ Error updating user:", e)
            return False
