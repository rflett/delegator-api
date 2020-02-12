import json

import boto3


class SecretsManager(object):
    def get_params(self) -> dict:
        """Get the secrets from AWS Secrets Manager"""
        secrets = boto3.client("secretsmanager")

        db_uri = self._get_db_uri(secrets)

        return {"DB_URI": db_uri}

    @staticmethod
    def _get_db_uri(secrets: boto3.client) -> str:
        """Get the RDS DB Uri from secrets manager"""
        response = secrets.get_secret_value(SecretId="rds-production")
        secret = json.loads(response["SecretString"])

        db_uri = f"postgresql://delegator:{secret['password']}@{secret['host']}:{secret['port']}/{secret['dbname']}"

        return db_uri
