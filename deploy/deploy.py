import argparse
import boto3
import json
import random
import string

ecs = boto3.client('ecs')


def service_exists(service: str, env: str) -> bool:
    """ Check if a service exists """
    services = ecs.describe_services(
        cluster=env,
        services=[service]
    )
    for _service in services.get('services'):
        if _service.get('serviceName') == service:
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
        cpu='256',
        memory='384',
        tags=tags
    )

    # common keyword args between create and update service functions
    common_service_kwargs = {
        'cluster': args.environment,
        'desiredCount': 1,
        'taskDefinition': args.service_name,
        'deploymentConfiguration': {
            'maximumPercent': 200,
            'minimumHealthyPercent': 0
        }
    }

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
