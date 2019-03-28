import datetime
import json
import typing
from app import logger, session_scope, g_response, j_response
from app.Controllers import AuthController
from app.Models import TaskType, User, Task, TaskStatus, TaskPriority, TaskTypeEscalation
from app.Models.Enums import TaskStatuses
from app.Models.RBAC import Operation, Resource
from flask import request, Response
from sqlalchemy import exists, and_, func
from sqlalchemy.orm import aliased


def _transition_task(task_id: int, status: str, req_user: User) -> None:
    """ Common function for transitioning a task """
    with session_scope():
        task_to_transition = TaskController.get_task_by_id(task_id)
        old_status = task_to_transition.status
        task_to_transition.status = status
        task_to_transition.status_changed_at = datetime.datetime.utcnow()

    req_user.log(
        operation=Operation.TRANSITION,
        resource=Resource.TASK,
        resource_id=task_id
    )
    logger.info(f"user {req_user.id} transitioned task {task_id} from {old_status} to {status}")


def _assign_task(task_id: int, assignee: int, req_user: User) -> None:
    """ Common function for assigning a task """
    with session_scope():
        task_to_assign = TaskController.get_task_by_id(task_id)
        task_to_assign.assignee = assignee

    req_user.log(
        operation=Operation.ASSIGN,
        resource=Resource.TASK,
        resource_id=task_id
    )
    logger.info(f"assigned task {task_id} to user {assignee}")


def _change_task_priority(task_id: int, priority: int) -> None:
    """ Common function for assigning a task """
    with session_scope():
        task_to_change = TaskController.get_task_by_id(task_id)
        task_to_change.priority = priority
        task_to_change.priority_changed_at = datetime.datetime.utcnow()

    logger.info(f"changed task {task_id} priority to {priority}")


def _make_task_dict(
    t: Task,
    ta: typing.Optional[User],
    tcb: User,
    ts: TaskStatus,
    tt: TaskType,
    tp: TaskPriority
) -> dict:
    """
    Creates a nice dict of a task
    :param t:   The task
    :param ta:  The task assignee
    :param tcb: The task created by
    :param ts:  The task status
    :param tt:  The task type
    :param tp:  The task priority
    :return:    A dict
    """
    extras = {
        'assignee': ta.as_dict() if ta is not None else None,
        'created_by': tcb.as_dict(),
        'status': ts.as_dict(),
        'type': _make_task_type_dict(tt),
        'priority': tp.as_dict()
    }

    task_dict = t.as_dict()

    # remove extras from base task
    for k in extras:
        task_dict.pop(k)

    # convert datetimes to str
    for k, v in task_dict.items():
        if isinstance(v, datetime.datetime):
            task_dict[k] = v.strftime("%Y-%m-%d %H:%M:%S%z")

    return dict(sorted({
        **task_dict,
        **extras
    }.items()))


def _make_task_type_dict(
        tt: TaskType
) -> dict:
    """ Creates a nice dict of a task type """
    task_type_dict = tt.as_dict()

    # get task type escalations
    with session_scope() as session:
        tte_qry = session.query(TaskTypeEscalation).filter(TaskTypeEscalation.task_type_id == tt.id).all()
        escalation_policies = [escalation.as_dict() for escalation in tte_qry]

    # sort by display order
    task_type_dict['escalation_policies'] = list(sorted(escalation_policies, key=lambda i: i['display_order']))

    return task_type_dict


class TaskController(object):
    @staticmethod
    def task_exists(task_id: int) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            return session.query(exists().where(Task.id == task_id)).scalar()

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
    def task_status_exists(task_status: str) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskStatus.status == task_status)).scalar()
        return ret

    @staticmethod
    def task_priority_exists(task_priority: int) -> bool:
        """ Checks to see if a task type exists. """
        with session_scope() as session:
            ret = session.query(exists().where(TaskPriority.priority == task_priority)).scalar()
        return ret

    @staticmethod
    def get_task_type_escalation(task_type_id: int, display_order: int):
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

    @staticmethod
    def get_assignee(task_id: int) -> typing.Union[int, None]:
        """ Gets the assignee for a task """
        with session_scope() as session:
            ret = session.query(Task).filter(Task.id == task_id).first()
        if ret is None:
            logger.info(f"No-one is assigned to task with id {task_id}")
            raise ValueError(f"No-one is assigned to task with id {task_id}")
        else:
            return ret.assignee

    @staticmethod
    def get_task_by_id(task_id: int) -> Task:
        """ Gets a task by its id """
        with session_scope() as session:
            ret = session.query(Task).filter(Task.id == task_id).first()
        if ret is None:
            logger.info(f"Task with id {task_id} does not exist.")
            raise ValueError(f"Task with id {task_id} does not exist.")
        else:
            return ret

    @staticmethod
    def get_task_priorities(req: request) -> Response:
        """ Returns all task priorities """
        from app.Controllers import AuthController
        from app.Models import TaskPriority

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.TASK_PRIORITIES
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            task_pr_qry = session.query(TaskPriority).all()

        task_priorities = [tp.as_dict() for tp in task_pr_qry]
        logger.debug(f"found {len(task_priorities)} task_priorities: {json.dumps(task_priorities)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_PRIORITIES
        )
        return j_response(task_priorities)

    @staticmethod
    def get_task_statuses(req: request) -> Response:
        """ Returns all task statuses """
        from app.Controllers import AuthController
        from app.Models import TaskStatus

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.TASK_STATUSES
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            task_st_qry = session.query(TaskStatus).all()

        task_statuses = [ts.as_dict() for ts in task_st_qry]
        logger.debug(f"found {len(task_statuses)} task statuses: {json.dumps(task_statuses)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_STATUSES
        )
        return j_response(task_statuses)

    @staticmethod
    def get_task_type_by_id(task_type_id: int) -> TaskType:
        """ Gets a task type by its id """
        with session_scope() as session:
            ret = session.query(TaskType).filter(TaskType.id == task_type_id).first()
        if ret is None:
            logger.info(f"Task Type with id {task_type_id} does not exist.")
            raise ValueError(f"Task Type with id {task_type_id} does not exist.")
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
            task_tt_qry = session.query(TaskType).filter(TaskType.org_id == req_user.org_id).all()

        task_types = [_make_task_type_dict(tt) for tt in task_tt_qry]
        logger.debug(f"found {len(task_types)} task types: {json.dumps(task_types)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASK_TYPES
        )
        return j_response(task_types)

    @staticmethod
    def get_task(task_id: int, req: request) -> Response:
        """ Get a single task. """
        from app.Controllers import TaskController

        try:
            task_id = int(task_id)
        except ValueError:
            return g_response(f"cannot cast `{task_id}` to int", 400)

        # if task exists check if permissions are good and then return the user
        if TaskController.task_exists(task_id):
            task = TaskController.get_task_by_id(task_id)
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.GET,
                resource=Resource.TASK,
                resource_org_id=task.org_id
            )
            # no perms
            if isinstance(req_user, Response):
                return req_user

            with session_scope() as session:
                task_assignee, task_created_by = aliased(User), aliased(User)
                tasks_qry = session.query(Task, task_assignee, task_created_by, TaskStatus, TaskType, TaskPriority)\
                    .outerjoin(task_assignee, task_assignee.id == Task.assignee)\
                    .join(task_created_by, task_created_by.id == Task.created_by)\
                    .join(Task.created_bys)\
                    .join(Task.task_statuses)\
                    .join(Task.task_types)\
                    .join(Task.task_priorities)\
                    .filter(Task.id == task_id)\
                    .first()

            task_as_dict = _make_task_dict(*tasks_qry)
            logger.debug(f"found task {task_as_dict}")
            req_user.log(
                operation=Operation.GET,
                resource=Resource.TASK,
                resource_id=task.id
            )
            return j_response(task_as_dict)

        else:
            logger.info(f"task with id {task_id} does not exist")
            return g_response("Task does not exist.", 400)

    @staticmethod
    def get_tasks(req: request) -> Response:
        """ Get all users """
        from app.Controllers import AuthController
        from app.Models import Task

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.GET,
            resource=Resource.TASKS
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            task_assignee, task_created_by = aliased(User), aliased(User)
            tasks_qry = session.query(Task, task_assignee, task_created_by, TaskStatus, TaskType, TaskPriority)\
                .outerjoin(task_assignee, task_assignee.id == Task.assignee)\
                .join(task_created_by, task_created_by.id == Task.created_by)\
                .join(Task.created_bys)\
                .join(Task.task_statuses)\
                .join(Task.task_types)\
                .join(Task.task_priorities)\
                .filter(Task.org_id == req_user.org_id)\
                .all()

        tasks = [_make_task_dict(t, ta, tcb, ts, tt, tp) for t, ta, tcb, ts, tt, tp in tasks_qry]
        logger.debug(f"found {len(tasks)} users: {json.dumps(tasks)}")
        req_user.log(
            operation=Operation.GET,
            resource=Resource.TASKS
        )
        return j_response(tasks)

    @staticmethod
    def create_task_types(req: request) -> Response:
        """ Create a task type """
        from app.Controllers import AuthController, ValidationController
        from app.Models import TaskType

        request_body = req.get_json()

        # validate task_type
        valid_tt = ValidationController.validate_create_task_type_request(request_body)
        # invalid task type
        if isinstance(valid_tt, Response):
            return valid_tt

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.CREATE,
            resource=Resource.TASK_TYPE,
            resource_org_id=valid_tt.get('org_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        if valid_tt.get('disabled') is None:
            with session_scope() as session:
                task_type = TaskType(
                    type=valid_tt.get('label'),
                    org_id=valid_tt.get('org_id')
                )
                session.add(task_type)
            req_user.log(
                operation=Operation.CREATE,
                resource=Resource.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.info(f"created task type {task_type.as_dict()}")
            return g_response("Successfully created task type", 201)
        else:
            with session_scope() as session:
                req_user = AuthController.authorize_request(
                    request_headers=req.headers,
                    operation=Operation.ENABLE,
                    resource=Resource.TASK_TYPE,
                    resource_org_id=valid_tt.get('org_id')
                )
                # no perms
                if isinstance(req_user, Response):
                    return req_user
                task_type = session.query(TaskType).filter(
                    and_(
                        TaskType.org_id == valid_tt.get('org_id'),
                        TaskType.label == valid_tt.get('label')
                    )
                ).first()
                task_type.disabled = False
            req_user.log(
                operation=Operation.ENABLE,
                resource=Resource.TASK_TYPE,
                resource_id=task_type.id
            )
            logger.info(f"enabled task type {task_type.as_dict()}")
            return g_response("Successfully enabled task type", 201)

    @staticmethod
    def create_task(req: request) -> Response:
        """
        Creates a task
        :param req: The request
        :return:        A response
        """
        from app.Controllers import ValidationController

        request_body = req.get_json()

        valid_task = ValidationController.validate_create_task_request(request_body)
        # invalid
        if isinstance(valid_task, Response):
            return valid_task

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.CREATE,
            resource=Resource.TASK,
            resource_org_id=valid_task.get('org_id')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        # create task
        with session_scope() as session:
            task = Task(
                org_id=valid_task.get('org_id'),
                type=valid_task.get('type'),
                description=valid_task.get('description'),
                status=valid_task.get('status'),
                time_estimate=valid_task.get('time_estimate'),
                due_time=valid_task.get('due_time'),
                assignee=None,
                priority=valid_task.get('priority'),
                created_by=req_user.id,
                created_at=valid_task.get('created_at'),
                finished_at=valid_task.get('finished_at')
            )
            session.add(task)

        req_user.log(
            operation=Operation.CREATE,
            resource=Resource.TASK,
            resource_id=task.id
        )
        logger.info(f"created task {task.as_dict()}")

        # optionally assign the task
        if valid_task.get('assignee') is not None:
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.ASSIGN,
                resource=Resource.TASK,
                resource_org_id=valid_task.get('org_id'),
                resource_user_id=valid_task.get('assignee')
            )
            # no auth
            if isinstance(req_user, Response):
                return req_user

            _assign_task(
                task_id=task.id,
                assignee=valid_task.get('assignee'),
                req_user=req_user
            )

        return g_response("Successfully created task", 201)

    @staticmethod
    def upsert_task_escalations(req: request) -> Response:
        """ Updates a task. Requires the full task object in the request. """
        from app.Controllers import ValidationController, TaskController
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

                req_user.log(
                    operation=Operation.CREATE,
                    resource=Resource.TASK_TYPE_ESCALATION,
                    resource_id=escalation.get('task_type_id')
                )
                logger.info(f"created task type escalation {new_escalation.as_dict()}")

            elif escalation.get('action') == 'update':
                total_updated += 1
                escalation_to_update = TaskController.get_task_type_escalation(
                    task_type_id=escalation.get('task_type_id'),
                    display_order=escalation.get('display_order')
                )
                with session_scope():
                    for k, v in escalation.items():
                        escalation_to_update.__setattr__(k, v)

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
    def update_task(task_id: int, req: request) -> Response:
        """ Updates a task. Requires the full task object in the request. """
        from app.Controllers import ValidationController, TaskController
        request_body = req.get_json()

        try:
            task_id = int(task_id)
        except ValueError:
            return g_response(f"cannot cast `{task_id}` to int", 400)

        valid_task = ValidationController.validate_update_task_request(task_id, request_body)
        # invalid task
        if isinstance(valid_task, Response):
            return valid_task

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.UPDATE,
            resource=Resource.TASK,
            resource_org_id=valid_task.get('org_id'),
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        # update the task
        task_to_update = TaskController.get_task_by_id(task_id)

        # assigning
        assignee = valid_task.pop('assignee', None)
        if task_to_update.assignee != assignee:
            req_user = AuthController.authorize_request(
                request_headers=req.headers,
                operation=Operation.ASSIGN,
                resource=Resource.TASK,
                resource_org_id=valid_task.get('org_id'),
                resource_user_id=valid_task.get('assignee')
            )
            # no perms
            if isinstance(req_user, Response):
                return req_user

            _assign_task(
                task_id=task_id,
                assignee=assignee,
                req_user=req_user
            )

        # transition
        task_status = valid_task.pop('status')
        if task_to_update.status != task_status:
            _transition_task(
                task_id=task_id,
                status=task_status,
                req_user=req_user
            )

        # change priority
        task_priority = valid_task.pop('priority')
        if task_to_update.priority != task_priority:
            _change_task_priority(
                task_id=task_id,
                priority=task_priority
            )

        # update other values
        with session_scope():
            for k, v in valid_task.items():
                task_to_update.__setattr__(k, v)

        req_user.log(
            operation=Operation.UPDATE,
            resource=Resource.TASK,
            resource_id=task_id
        )
        logger.info(f"updated task {task_to_update.as_dict()}")
        return g_response(status=204)

    @staticmethod
    def assign_task(req: request) -> Response:
        """ Assigns a user to task """
        from app.Controllers import ValidationController

        valid_assignment = ValidationController.validate_assign_task(req.get_json())
        # invalid assignment
        if isinstance(valid_assignment, Response):
            return valid_assignment

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.ASSIGN,
            resource=Resource.TASK,
            resource_org_id=valid_assignment.get('org_id'),
            resource_user_id=valid_assignment.get('assignee')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        _assign_task(
            task_id=valid_assignment.get('task_id'),
            assignee=valid_assignment.get('assignee'),
            req_user=req_user
        )

        return g_response(status=204)

    @staticmethod
    def drop_task(task_id, req: request) -> Response:
        """ Drops a task, which sets it to READY and removes the assignee """
        from app.Controllers import ValidationController, TaskController

        try:
            task_id = int(task_id)
        except ValueError:
            return g_response(f"cannot cast `{task_id}` to int", 400)

        valid_task_drop = ValidationController.validate_drop_task(task_id)
        # invalid task drop request
        if isinstance(valid_task_drop, Response):
            return valid_task_drop

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.DROP,
            resource=Resource.TASK,
            resource_org_id=valid_task_drop.get('org_id'),
            resource_user_id=valid_task_drop.get('assignee')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        task_to_drop = TaskController.get_task_by_id(valid_task_drop.get('task_id'))

        with session_scope():
            task_to_drop.assignee = None
            task_to_drop.status = TaskStatuses.READY

        req_user.log(
            operation=Operation.DROP,
            resource=Resource.TASK,
            resource_id=task_id
        )
        logger.info(f"user {req_user.id} dropped task {task_to_drop.id} "
                    f"which was assigned to {valid_task_drop.get('assignee')}")
        return g_response(status=204)

    @staticmethod
    def transition_task(req: request) -> Response:
        """ Transitions the status of a task """
        from app.Controllers import ValidationController

        valid_task_transition = ValidationController.validate_transition_task(request.get_json())
        # invalid
        if isinstance(valid_task_transition, Response):
            return valid_task_transition

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.TRANSITION,
            resource=Resource.TASK,
            resource_org_id=valid_task_transition.get('org_id'),
            resource_user_id=valid_task_transition.get('assignee')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        _transition_task(
            task_id=valid_task_transition.get('task_id'),
            status=valid_task_transition.get('task_status'),
            req_user=req_user
        )

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

        req_user.log(
            operation=Operation.DISABLE,
            resource=Resource.TASK_TYPE,
            resource_id=valid_dtt.id
        )
        logger.info(f"disabled task type {valid_dtt.as_dict()}")
        return g_response("Successfully disabled task type", 201)

    @staticmethod
    def delay_task(req: request) -> Response:
        """ Transitions the status of a task """
        from app.Controllers import ValidationController
        from app.Models import DelayedTask

        valid_delay_task = ValidationController.validate_delay_task_request(request.get_json())
        # invalid
        if isinstance(valid_delay_task, Response):
            return valid_delay_task

        req_user = AuthController.authorize_request(
            request_headers=req.headers,
            operation=Operation.DELAY,
            resource=Resource.TASK,
            resource_org_id=valid_delay_task.get('org_id'),
            resource_user_id=valid_delay_task.get('assignee')
        )
        # no perms
        if isinstance(req_user, Response):
            return req_user

        with session_scope() as session:
            # set task to delayed
            _transition_task(
                task_id=valid_delay_task.get('task_id'),
                status=TaskStatuses.DELAYED,
                req_user=req_user
            )
            # created delayed until
            delay = session.query(DelayedTask).filter(
                    DelayedTask.task_id == valid_delay_task.get('task_id')
                ).first()
            if delay is not None:
                delay.delay_for = valid_delay_task.get('delay_for')
                delay.delayed_at = datetime.datetime.utcnow()
            else:
                delayed_task = DelayedTask(
                    task_id=valid_delay_task.get('task_id'),
                    delay_for=valid_delay_task.get('delay_for')
                )
                session.add(delayed_task)

        req_user.log(
            operation=Operation.DELAY,
            resource=Resource.TASK,
            resource_id=valid_delay_task.get('task_id')
        )
        logger.info(f"user {req_user.id} delayed task {valid_delay_task.get('task_id')} "
                    f"until {valid_delay_task.get('delay_for')}")
        return g_response(status=204)
