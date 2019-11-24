import boto3


class SsmConfig(object):

    def get_params(self, app_env: str) -> dict:
        """Get the parameters from parameter store"""
        ssm = boto3.client('ssm')
        return {
            **self._get_param_path(ssm, app_env, 'global'),
            **self._get_param_path(ssm, app_env, 'delegator-api')
        }

    @staticmethod
    def _get_param_path(ssm, app_env: str, path: str) -> dict:
        """Get params for a particular path"""
        ret = {}
        params_qry = ssm.get_parameters_by_path(Path=f"/{app_env.lower()}/application/{path}/")

        for param in params_qry['Parameters']:
            # break up /staging/application/global/db-uri to just db-uri
            name = param['Name'].split('/')[-1:][0]
            # db-uri -> DB_URI
            name = name.replace('-', '_').upper()
            ret[name] = param['Value']

        return ret
