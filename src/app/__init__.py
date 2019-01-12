from flask import Flask
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# flask conf
app = Flask(__name__)
app.config.from_object(f"config.{getenv('APP_ENV', 'Local')}")

# db conf
engine = create_engine(f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{app.config['DB_HOST']}/etemt")
DBSession = sessionmaker(bind=engine)
DBBase = declarative_base()

# routes
from app import routes
