from flask import Flask
from os import getenv

app = Flask(__name__)

app.config.from_object(f"config.{getenv('APP_ENV', 'Local')}")

from app import routes
