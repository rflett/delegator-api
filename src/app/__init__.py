from flask import Flask
from os import getenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# flask conf
app = Flask(__name__)
app.config.from_object(f"config.{getenv('APP_ENV', 'Local')}")

# db conf
if getenv('APP_ENV') == 'Scott':
    import boto3
    # scott's access token, don't do this
    ec2 = boto3.client(
        'ec2',
        aws_access_key_id='AKIAICFBPHVQZAU4TZWA',
        aws_secret_access_key='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'
    )
    api_staging = ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    'api-staging',
                ]
            },
        ]
    )
    db_ip = api_staging.get('Reservations')[0].get('Instances')[0].get('PublicIpAddress')
    engine = create_engine(f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{db_ip}/etemt")
else:
    engine = create_engine(
        f"postgresql://{app.config['DB_USER']}:{app.config['DB_PASS']}@{app.config['DB_HOST']}/etemt")

DBSession = sessionmaker(bind=engine)
DBBase = declarative_base()

# routes
from app import routes
