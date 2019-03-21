import argparse
import boto3
import json
import random
import string

ecs = boto3.client('ecs')

# settings
desired_count = 1
min_health_pc = 0
max_health_pc = 200
task_role_arn = 'arn:aws:iam::008492826001:role/afterburner-api-container'


def service_exists(service: str, env: str) -> bool:
    """ Check if a service exists """
    services = ecs.describe_services(
        cluster=env,
        services=[service]
    )
    for _service in services.get('services'):
        if _service.get('status') == 'ACTIVE' and _service.get('serviceName') == service:
            return True
    return False


if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("service_name", help="The name of the service", type=str)
    parser.add_argument("environment", help="The environment to deploy this service to", type=str)
    args = parser.parse_args()

    # resource tags
    tags = [
        {
            'key': 'environment',
            'value': args.environment
        },
        {
            'key': 'source',
            'value': args.service_name
        }
    ]

    # register a new task definition
    register_res = ecs.register_task_definition(
        family=args.service_name,
        networkMode='host',
        containerDefinitions=json.load(open('deploy/container_definitions.json')),
        tags=tags
    )

    # common keyword args between create and update service functions
    common_service_kwargs = {
        'cluster': args.environment,
        'desiredCount': desired_count,
        'taskDefinition': args.service_name,
        'deploymentConfiguration': {
            'maximumPercent': max_health_pc,
            'minimumHealthyPercent': min_health_pc
        }
    }
    if task_role_arn is not None:
        common_service_kwargs['taskRoleArn'] = task_role_arn

    # update or create service
    if service_exists(args.service_name, args.environment):
        ecs.update_service(
            **common_service_kwargs,
            service=args.service_name,
            forceNewDeployment=True
        )
    else:
        ecs.create_service(
            **common_service_kwargs,
            serviceName=args.service_name,
            clientToken=''.join(random.choices(string.ascii_uppercase + string.digits, k=20)),
            launchType='EC2',
            placementStrategy=[
                {
                    'type': 'spread',
                    'field': 'attribute:ecs.availability-zone'
                }
            ],
            schedulingStrategy='REPLICA',
            deploymentController={
                'type': 'ECS'
            }
        )
