import json
import typing
from app import logger, session_scope, g_response, j_response
from app.Controllers import AuthController
from app.Models import TaskType, TaskTypeEscalation, Notification
from app.Models.Enums import Events
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, and_, func


def _get_task_type_escalation(task_type_id: int, display_order: int):
    """ Gets a task type escalation """
    with session_scope() as session:
        ret = session.query(TaskTypeEscalation).filter(
            and_(
                TaskTypeEscalation.task_type_id == task_type_id,
                TaskTypeEscalation.display_order == display_order
            )
        ).first()
    if ret is None:
        logger.info(f"No task type escalation with task_type_id {task_type_id} and display order {display_order}")
        raise ValueError(f"No task type escalation with "
                         f"task_type_id {task_type_id} and display order {display_order}")
    else:
        return ret


def _get_task_type_by_id(task_type_id: int) -> TaskType:
    """ Gets a task type by its id """
    with session_scope() as session:
        ret = session.query(TaskType).filter(TaskType.id == task_type_id).first()
    if ret is None:
        logger.info(f"Task Type with id {task_type_id} does not exist.")
        raise ValueError(f"Task Type with id {task_type_id} does not exist.")
    else:
        return ret


class TaskTypeController(object):
    @staticmethod
    def task_type_enabled(task_type_identifier: typing.Union[str, int], org_identifier: int) -> bool:
        """ Checks to see if a task type is enabled. """
        with session_scope() as session:
            if isinstance(task_type_identifier, int):
                logger.info(f"task type identifier is an int so finding by id")
                return session.query(exists().where(
                    and_(
                        TaskType.id == task_type_identifier,
                        TaskType.disabled == False  # noqa
                    )
                )).scalar()
            elif isinstance(task_type_identifier, str):
                logger.info(f"task type identifier is a str so finding by type")
                return session.query(exists().where(
                    and_(
                        TaskType.label == task_type_identifier,
                        TaskType.org_id == org_identifier,
                        TaskType.disabled == False  # noqa
                    )
                )).scalar()

    @staticmethod
    def task_type_exists(
            task_type_identifier: typing.Union[str, int],
            org_identifier: typing.Optional[int] = None
    ) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            if isinstance(task_type_identifier, int):
                logger.info(f"task type identifier is an int so finding by id")
                return session.query(exists().where(
                    TaskType.id == task_type_identifier
                )
                ).scalar()
            elif isinstance(task_type_identifier, str):
                logger.info(f"task type identifier is a str so finding by type")
                return session.query(exists().where(
                    and_(
                        func.lower(TaskType.label) == func.lower(task_type_identifier),
                        TaskType.org_id == org_identifier
                    )
                )).scalar()

    @staticmethod
    def get_task_type_by_id(task_type_id: int) -> TaskType:
        """ Gets a task type by its id """
        return _get_task_type_by_id(task_type_id)

    @staticmethod
    def get_task_type_by_label(label: str, org_id: int) -> TaskType:
        """ Gets a task type by its label """
        with session_scope() as session:
            ret = session.query(TaskType).filter(
                and_(
                    func.lower(TaskType.label) == func.lower(label),
                    TaskType.org_id == org_id
                )
            ).first()
        if ret is None:
            logger.info(f"Task Type with label {label} does not exist in org {org_id}.")
            raise ValueError(f"Task Type with label {label} does not existin org {org_id}")
        else:
            return ret

    @staticmethod
    def get_task_types(req: request) -> Response:
        """ Returns all task types """
        from app.Controllers import AuthController
        from app.Models import TaskType

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.TASK_TYPES
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            task_type_query = session.query(TaskType).filter(TaskType.org_id == req_user.org_id).all()

        task_types = [tt.fat_dict() for tt in task_type_query]
        logger.debug(f"found {len(task_types)} task types: {json.dumps(task_types)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_TYPES
        )
        return j_response(task_types)

    @staticmethod
    def create_task_type(req: request) -> Response:
        """ Create a task type """
        from app.Controllers import AuthController, ValidationController
        from app.Models import TaskType

        request_body = req.get_json()

        # validate task_type
        validate_res = ValidationController.validate_create_task_type_request(request_body)

        if isinstance(validate_res, Response):
            return validate_res

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.CREATE,
            resource=Resource.TASK_TYPE,
            resource_org_id=request_body.get('org_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        if isinstance(validate_res, str):
            # it will be a string it's new
            with session_scope() as session:
                task_type = TaskType(
                    label=validate_res,
                    org_id=request_body.get('org_id')
                )
                session.add(task_type)
            Notification(
                org_id=task_type.org_id,
                event=Events.tasktype_created,
                event_id=task_type.id,
            ).publish()
            Notification(
                org_id=req_user.org_id,
                event=Events.user_created_tasktype,
                event_id=req_user.id,
                event_friendly=f"Created task type {task_type.label}."
            ).publish()
            req_user.log(
                operation=Operation.CREATE,
                resource=Resource.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.info(f"created task type {task_type.as_dict()}")
            return g_response("Successfully created task type", 201)
        elif isinstance(validate_res, TaskType):
            # it will be a TaskType object if it exists already and needs to be enabled
            with session_scope():
                req_user = AuthController.authorize_request(
                    request_headers=req.headers,
                    operation=Operation.ENABLE,
                    resource=Resource.TASK_TYPE,
                    resource_org_id=validate_res.org_id
                )
                # no perms
                if isinstance(req_user, Response):
                    return req_user
                validate_res.disabled = False
            Notification(
                org_id=validate_res.org_id,
                event=Events.tasktype_enabled,
                event_id=validate_res.id
            ).publish()
            req_user.log(
                operation=Operation.ENABLE,
                resource=Resource.TASK_TYPE,
                resource_id=validate_res.id
            )
            logger.info(f"enabled task type {validate_res.as_dict()}")
            return g_response("Successfully enabled task type", 201)

    @staticmethod
    def upsert_task_escalations(req: request) -> Response:
        """ Updates a task. Requires the full task object in the request. """
        from app.Controllers import ValidationController
        from app.Controllers.ValidationController import _check_task_type_id, _check_org_id
        request_body = req.get_json()
        total_updated = total_created = total_deleted = 0

        # VALIDATION
        escalations = request_body.get('escalation_policies')
        if escalations is None or not isinstance(escalations, list):
            return g_response("Missing escalations", 400)
        task_type_id = _check_task_type_id(request_body.get('task_type_id'), should_exist=True)
        if isinstance(task_type_id, Response):
            return task_type_id
        org_id = _check_org_id(request_body.get('org_id'), should_exist=True)
        if isinstance(org_id, Response):
            return org_id

        valid_escalations = ValidationController.validate_upsert_task_escalation(escalations)
        # invalid
        if isinstance(valid_escalations, Response):
            return valid_escalations

        # AUTHORIZATION
        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.UPSERT,
            resource=Resource.TASK_TYPE_ESCALATION,
            resource_org_id=org_id,
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        # UPSERT
        for escalation in valid_escalations:
            if escalation.get('action') == 'create':
                total_created += 1
                with session_scope() as session:
                    new_escalation = TaskTypeEscalation(
                        task_type_id=escalation.get('task_type_id'),
                        display_order=escalation.get('display_order'),
                        delay=escalation.get('delay'),
                        from_priority=escalation.get('from_priority'),
                        to_priority=escalation.get('to_priority')
                    )
                    session.add(new_escalation)

                Notification(
                    org_id=org_id,
                    event=Events.tasktype_escalation_created,
                    event_id=new_escalation.task_type_id
                ).publish()
                Notification(
                    org_id=req_user.org_id,
                    event=Events.user_created_tasktype_escalation,
                    event_id=req_user.id,
                    event_friendly=f"Created escalation for task type "
                    f"{_get_task_type_by_id(new_escalation.task_type_id).label}."
                ).publish()
                req_user.log(
                    operation=Operation.CREATE,
                    resource=Resource.TASK_TYPE_ESCALATION,
                    resource_id=escalation.get('task_type_id')
                )
                logger.info(f"created task type escalation {new_escalation.as_dict()}")

            elif escalation.get('action') == 'update':
                total_updated += 1
                escalation_to_update = _get_task_type_escalation(
                    task_type_id=escalation.get('task_type_id'),
                    display_order=escalation.get('display_order')
                )
                with session_scope():
                    for k, v in escalation.items():
                        escalation_to_update.__setattr__(k, v)

                    Notification(
                        org_id=org_id,
                        event=Events.tasktype_escalation_updated,
                        event_id=escalation_to_update.task_type_id
                    ).publish()
                    Notification(
                        org_id=req_user.org_id,
                        event=Events.user_created_tasktype_escalation,
                        event_id=req_user.id,
                        event_friendly=f"Updated escalation for task type "
                        f"{_get_task_type_by_id(escalation_to_update.task_type_id).label}."
                    ).publish()
                    req_user.log(
                        operation=Operation.UPDATE,
                        resource=Resource.TASK_TYPE_ESCALATION,
                        resource_id=escalation.get('task_type_id')
                    )
                logger.info(f"updated task type escalation {escalation_to_update.as_dict()}")

        # DELETE MISMATCH
        # get escalations in request as a set of tuples
        request_escalations = {(e.get('task_type_id'), e.get('display_order')) for e in valid_escalations}

        with session_scope() as session:
            # get escalations which exist in the db as a set of tuples
            db_esc_qry = session.query(TaskTypeEscalation.task_type_id, TaskTypeEscalation.display_order)\
                .filter(TaskTypeEscalation.task_type_id == task_type_id).all()
            db_escalations = {e for e in db_esc_qry}

            # remove those that exist in the db that didn't in the request
            to_remove = db_escalations - request_escalations
            for r in to_remove:
                total_deleted += 1
                session.query(TaskTypeEscalation).filter(
                    and_(
                        TaskTypeEscalation.task_type_id == r[0],
                        TaskTypeEscalation.display_order == r[1]
                    )
                ).delete(synchronize_session=False)
                logger.info(f"deleted task type escalation with task_type_id:{r[0]}, display_order:{r[1]}")

        logger.info(f"upsert task type escalations finished. "
                    f"created:{total_created}, updated:{total_updated}, deleted:{total_deleted}")
        # SUCCESS
        return g_response(status=204)

    @staticmethod
    def disable_task_type(task_type_id: int, req: request) -> Response:
        """ Disables a task type """
        from app.Controllers import AuthController, ValidationController

        try:
            task_type_id = int(task_type_id)
        except ValueError:
            return g_response(f"cannot cast `{task_type_id}` to int", 400)

        valid_dtt = ValidationController.validate_disable_task_type_request(task_type_id)
        # invalid
        if isinstance(valid_dtt, Response):
            return valid_dtt

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.DISABLE,
            resource=Resource.TASK_TYPE,
            resource_org_id=valid_dtt.org_id
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope():
            valid_dtt.disabled = True

        Notification(
            org_id=valid_dtt.org_id,
            event=Events.tasktype_disabled,
            event_id=valid_dtt.id,
        ).publish()
        Notification(
            org_id=req_user.org_id,
            event=Events.user_disabled_tasktype,
            event_id=req_user.id,
            event_friendly=f"Disabled task type {valid_dtt.label}"
        ).publish()
        req_user.log(
            operation=Operation.DISABLE,
            resource=Resource.TASK_TYPE,
            resource_id=valid_dtt.id
        )
        logger.info(f"disabled task type {valid_dtt.as_dict()}")
        return g_response(status=204)
