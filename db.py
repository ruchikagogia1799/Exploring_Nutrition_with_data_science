# db.py — handles all database interactions
import os
import bcrypt
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, Text
from sqlalchemy.sql import select, and_, or_
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# ------------------- Database Setup -------------------
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgres://user:pass@host/dbname

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
metadata = MetaData()

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

Session = sessionmaker(bind=engine)


# ------------------- Helpers -------------------
def _row_to_dict(row):
    """Convert SQLAlchemy Row to dict safely"""
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    return dict(row)


# ------------------- CRUD Functions -------------------
def user_exists(username, email):
    with Session() as ses:
        q = select(users).where(or_(
            users.c.username == username,
            users.c.email == email
        ))
        return ses.execute(q).fetchone() is not None


def register_user(username, email, password, weight, height, age, gender, activity):
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
            print("Error registering user:", e)
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
            print("Error updating user:", e)
            return False
