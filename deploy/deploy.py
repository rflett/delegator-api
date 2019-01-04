import boto3
import json
import random
import string
import sys

ecs = boto3.client('ecs')
service_name = sys.argv[1]
environment = sys.argv[2]

tags = [
    {
        'key': 'environment',
        'value': environment
    },
    {
        'key': 'source',
        'value': service_name
    }
]

# register a new task definition
register_res = ecs.register_task_definition(
    family=service_name,
    networkMode='bridge',
    containerDefinitions=json.load(open('deploy/container_definitions.json')),
    cpu='256',
    memory='256',
    tags=tags
)

# check if service exists
service_exists = False
services = ecs.describe_services(
    cluster=environment,
    services=[service_name]
)
for _service in services.get('services'):
    if _service.get('serviceName') == service_name:
        service_exists = True

# update or create service
common_service_settings = {
    'cluster': environment,
    'desiredCount': 1,
    'taskDefinition': service_name,
    'deploymentConfiguration': {
        'maximumPercent': 200,
        'minimumHealthyPercent': 50
    }
}
if service_exists:
    ecs.update_service(
        **common_service_settings,
        service=service_name,
        forceNewDeployment=True
    )
else:
    ecs.create_service(
        **common_service_settings,
        serviceName=service_name,
        clientToken=''.join(random.choices(string.ascii_uppercase + string.digits, k=20)),
        launchType='EC2',
        placementStrategy=[
            {
                'type': 'spread',
                'field': 'attribute:ecs.availability-zone'
            },
        ],
        schedulingStrategy='REPLICA',
        deploymentController={
            'type': 'ECS'
        }
    )
