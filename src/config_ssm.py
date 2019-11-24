import boto3


class SsmConfig(object):

    def get_params(self, app_env: str) -> dict:
        """Get the parameters from parameter store"""
        s = boto3.Session(profile_name="production")
        ssm = s.client('ssm')
        return {
            **self._get_param_path(ssm, app_env, 'global'),
            **self._get_param_path(ssm, app_env, 'delegator-api')
        }

    @staticmethod
    def _get_param_path(ssm, app_env: str, path: str) -> dict:
        """Get params for a particular path"""
        ret = {}
        global_params_req = ssm.get_parameters_by_path(Path=f"/{app_env}/application/{path}")

        for param in global_params_req['Parameters']:
            # break up /staging/application/global/db-uri to just db-uri
            name = param['Name'].split('/')[-1:][0]
            # db-uri -> DB_URI
            name = name.replace('-', '_').upper()
            ret[name] = param['Value']

        return ret
