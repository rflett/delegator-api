import argparse
import boto3
import json
import random
import string
import typing

ecs = boto3.client('ecs')
sd = boto3.client('servicediscovery')

# settings
sd_namespace_id = 'ns-hbsymg3dzxrg2tsn'
container_port = 5000
desired_count = 1
min_health_pc = 0
max_health_pc = 200


def get_sd_service_arn(service_name: str) -> typing.Optional[str]:
    """ Return the service ARN for a SD service """
    existing_services = sd.list_services().get('Services')
    for existing_svc in existing_services:
        if existing_svc.get('Name') == service_name:
            return existing_svc.get('Arn')
    return None


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

    # service discovery
    sd_service_name = f"{args.service_name}-{args.environment}"
    sd_service_arn = get_sd_service_arn(sd_service_name)

    if sd_service_arn is None:
        # create sd service
        sd.create_service(
            Name=sd_service_name,
            NamespaceId=sd_namespace_id,
            Description=sd_service_name,
            DnsConfig={
                'NamespaceId': sd_namespace_id,
                'RoutingPolicy': 'WEIGHTED',
                'DnsRecords': [
                    {
                        'Type': 'SRV',
                        'TTL': 10
                    }
                ]
            },
            HealthCheckCustomConfig={
                'FailureThreshold': 1
            }
        )
        # get new service id
        sd_service_arn = get_sd_service_arn(sd_service_name)

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
            },
            serviceRegistries=[
                {
                    'registryArn': sd_service_arn,
                    'containerName': args.service_name,
                    'containerPort': container_port
                }
            ]
        )
