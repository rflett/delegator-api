import datetime
from collections import namedtuple

from flask import request, Response

import app.Exceptions
from app import r_cache, j_response, logger, session_scope, app  # noqa
from app.Controllers import AuthenticationController, AuthorizationController
from app.Models.Enums import Operations, Resources


def clean_qry(qry) -> list:
    Record = namedtuple('Record', qry.keys())
    records = [dict(Record(*r)._asdict()) for r in qry.fetchall()]

    for record in records:
        for k, v in record.items():
            if type(v) == datetime.datetime:
                record[k] = v.strftime(app.config['RESPONSE_DATE_FORMAT'])

    return records


def completed_tasks(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' || u.last_name AS name,
                   tt.label AS task_type,
                   t.finished_at AS finished_at
            FROM tasks t INNER JOIN task_types tt
                         ON t.type = tt.id
                         INNER JOIN users u
                         ON u.id = t.finished_by
            WHERE t.finished_at IS NOT NULL
            AND t.org_id = :org_id
            ORDER BY t.finished_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def delayed_tasks(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
            u.first_name || ' ' || u.last_name AS name,
            tt.label AS task_type,
            td.delayed_at AS delayed_at
            FROM users u INNER JOIN tasks_delayed td
                         ON u.id = td.delayed_by
                         INNER JOIN tasks t
                         ON td.task_id = t.id
                         INNER JOIN task_types tt
                         ON t.type = tt.id
            WHERE u.org_id = :org_id
            ORDER BY td.delayed_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def dropped_tasks(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' || u.last_name AS name,
                   tt.label AS task_type,
                   r.created_at AS dropped_at
            FROM task_types tt INNER JOIN tasks t
                               ON tt.id = t.type
                               INNER JOIN rbac_audit_log r
                               ON t.id = r.resource_id
                               INNER JOIN users u
                               ON r.user_id = u.id
            WHERE r.operation = 'DROP'
            AND r.resource = 'TASK'
            AND t.org_id = :org_id
            ORDER BY r.created_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def task_statuses(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' || u.last_name AS name,
                   tt.label AS task_type,
                   ts.label AS "status",
                   t.status_changed_at AS status_changed_at
            FROM users u RIGHT JOIN tasks t
                         ON u.id = t.assignee
                         INNER JOIN task_types tt
                         ON t.type = tt.id
                         INNER JOIN task_statuses ts
                         ON t.status = ts.status
            WHERE t.status <> 'COMPLETED'
            AND u.org_id = :org_id
            ORDER BY t.status_changed_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def task_priorities(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' || u.last_name AS name,
                   tt.label AS task_type,
                   tp.label AS "priority",
                   t.priority_changed_at AS priority_changed_at
            FROM users u RIGHT JOIN tasks t
                         ON u.id = t.assignee
                         INNER JOIN task_types tt
                         ON t.type = tt.id
                         INNER JOIN task_priorities tp
                         ON t.priority = tp.priority
            WHERE u.org_id = :org_id
            ORDER BY t.priority_changed_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def tasks_created(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' ||
                   u.last_name AS name, tt.label AS task_type,
                   t.created_at AS created_at
            FROM users u INNER JOIN tasks t
                         ON u.id = t.created_by
                         INNER JOIN task_types tt
                         ON t.type = tt.id
            WHERE u.org_id = :org_id
            ORDER BY t.created_at ASC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def time_to_start(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT tt.label AS task_type, EXTRACT(EPOCH FROM (t.started_at - t.created_at)) AS time_to_start
            FROM tasks t INNER JOIN task_types tt
                         ON t.type = tt.id
            WHERE t.started_at IS NOT NULL
            AND t.org_id = :org_id
            ORDER BY time_to_start DESC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def time_to_finish(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.id AS user_id,
                   u.first_name || ' ' || u.last_name AS name,
                   t.id AS task_id,
                   tt.label AS task_type,
                   EXTRACT(EPOCH FROM (t.finished_at - t.created_at)) AS time_to_finish
            FROM users u INNER JOIN tasks t
                         ON u.id = t.finished_by
                         INNER JOIN task_types tt
                         ON t.type = tt.id
            WHERE t.finished_at IS NOT NULL
            AND u.org_id = :org_id
            ORDER BY time_to_finish DESC
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


def delays_per_task(org_id: int) -> list:
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT t.id, SUM(td.delay_for) AS delayed_for
            FROM tasks_delayed td INNER JOIN tasks t
                                  ON td.task_id = t.id
            WHERE t.org_id = :org_id
            GROUP BY t.id
            """,
            {'org_id': org_id}
        )

    return clean_qry(qry)


class ReportController(object):
    @staticmethod
    def get_all(req: request) -> Response:
        """ Get all reports """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        # reports = r_cache.hgetall(req_user.org_id)
        # TODO this is a temporary way of pulling the reports for development
        # Once I'm happy they won't change much they should be moved to the reporting-cruncher and cached in redis.
        reports = {
            "completed_tasks": completed_tasks(req_user.org_id),
            "delayed_tasks": delayed_tasks(req_user.org_id),
            "dropped_tasks": dropped_tasks(req_user.org_id),
            "task_statuses": task_statuses(req_user.org_id),
            "task_priorities": task_priorities(req_user.org_id),
            "tasks_created": tasks_created(req_user.org_id),
            "time_to_start": time_to_start(req_user.org_id),
            "time_to_finish": time_to_finish(req_user.org_id),
            "delays_per_task": delays_per_task(req_user.org_id),
        }

        logger.debug("retrieved reports")
        return j_response(reports)
