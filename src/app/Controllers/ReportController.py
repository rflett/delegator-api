import datetime
import typing
from collections import namedtuple
from dateutil import tz

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


def completed_tasks(org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
    start_period, end_period = period
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
            WHERE t.finished_at BETWEEN :start_period AND :end_period
            AND t.org_id = :org_id
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def delayed_tasks(org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
    start_period, end_period = period
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
            WHERE td.delayed_at BETWEEN :start_period AND :end_period
            AND u.org_id = :org_id
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def dropped_tasks(org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
    start_period, end_period = period
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
            WHERE r.created_at BETWEEN :start_period AND :end_period
            AND r.operation = 'DROP'
            AND r.resource = 'TASK'
            AND t.org_id = :org_id
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def tasks_created(org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
    start_period, end_period = period
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
            WHERE t.created_at BETWEEN :start_period AND :end_period
            AND u.org_id = :org_id
            ORDER BY t.created_at ASC
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


class ReportController(object):
    @staticmethod
    def get_trends(req: request) -> Response:
        """ Get completed tasks """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_today = datetime.datetime(now.year, now.month, now.day, tzinfo=tz.tzutc())
        yesterday = now - datetime.timedelta(
            days=1,
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
        )
        start_of_this_week = start_of_today - datetime.timedelta(days=now.weekday())
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        reports = []
        periods = [
            ('today_so_far', start_of_today),
            ('yesterday', yesterday),
            ('this_week_so_far', start_of_this_week),
            ('start_of_this_month', start_of_this_month)
        ]

        for period in periods:
            reports.append({
                "period": period[0],
                "created": len(tasks_created(req_user.org_id, (period[1], now))),
                "completed": len(completed_tasks(req_user.org_id, (period[1], now))),
                "delayed": len(delayed_tasks(req_user.org_id, (period[1], now))),
                "dropped": len(dropped_tasks(req_user.org_id, (period[1], now)))
            })

        return j_response(reports)

    @staticmethod
    def get_start_and_finish_times(req: request) -> Response:
        """ Get time to start and time to finish for tasks """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        with session_scope() as session:
            qry = session.execute(
                """
                SELECT tt.label AS task_type,
                       AVG(EXTRACT(EPOCH FROM (t.started_at - t.created_at))) AS time_to_start,
                       AVG(EXTRACT(EPOCH FROM (t.finished_at - t.created_at))) AS time_to_finish
                FROM tasks t INNER JOIN task_types tt
                             ON t.type = tt.id
                WHERE t.created_at BETWEEN :start_period AND :end_period
                AND t.started_at BETWEEN :start_period AND :end_period
                AND t.finished_at BETWEEN :start_period AND :end_period
                AND t.org_id = :org_id
                GROUP BY tt.label
                ORDER BY time_to_finish DESC
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            "time_to_start_and_finish": clean_qry(qry)
        })

    @staticmethod
    def top_five_slowest_tasks(req: request) -> Response:
        """ Get the 5 tasks with longest time to finish """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        with session_scope() as session:
            qry = session.execute(
                """
                SELECT t.description AS description
                       u.first_name || ' ' || u.last_name AS finished_by,
                       tt.label AS task_type,
                       AVG(EXTRACT(EPOCH FROM (t.finished_at - t.created_at))) AS time_to_finish
                FROM users u RIGHT JOIN tasks t
                             ON u.id = t.finished_by
                             INNER JOIN task_types tt
                             ON t.type = tt.id
                WHERE t.created_at BETWEEN :start_period AND :end_period
                AND t.finished_at BETWEEN :start_period AND :end_period
                AND t.org_id = :org_id
                ORDER BY time_to_finish DESC
                LIMIT 5
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            'top_five_slowest_tasks': clean_qry(qry)
        })

    @staticmethod
    def average_time_to_start_a_task(req: request) -> Response:
        """ Get the average time to start a task """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        with session_scope() as session:
            qry = session.execute(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (t.started_at - t.created_at))) AS time_to_start,
                FROM tasks t
                WHERE t.created_at BETWEEN :start_period AND :end_period
                AND t.started_at BETWEEN :start_period AND :end_period
                AND t.org_id = :org_id
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            'average_time_to_start': clean_qry(qry)
        })

    @staticmethod
    def total_tasks_completed(req: request) -> Response:
        """ Get the average time to start a task """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        return j_response({
            'top_five_slowest_tasks': completed_tasks(req_user.org_id, (start_of_this_month, now))
        })

    @staticmethod
    def tasks_by_priority(req: request) -> Response:
        """ Get the average time to start a task """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

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
                WHERE t.priority_changed_at BETWEEN :start_period AND :end_period
                AND u.org_id = :org_id
                ORDER BY t.priority_changed_at ASC
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            'tasks_by_priority': clean_qry(qry)
        })

    @staticmethod
    def tasks_by_status(req: request) -> Response:
        """ Get the average time to start a task """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

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
                WHERE t.status_changed_at BETWEEN :start_period AND :end_period
                AND t.status <> 'COMPLETED'
                AND u.org_id = :org_id
                ORDER BY t.status_changed_at ASC
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            'tasks_by_status': clean_qry(qry)
        })

    @staticmethod
    def delays_per_task_type(req: request) -> Response:
        """ Get time to start and time to finish for tasks """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        now = datetime.datetime.utcnow()
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        with session_scope() as session:
            qry = session.execute(
                """
                SELECT tt.label, SUM(td.delay_for) AS delayed_for
                FROM tasks_delayed td INNER JOIN tasks t
                                      ON td.task_id = t.id
                                      INNER JOIN task_types tt
                                      ON t.type = tt.id
                WHERE t.delayed_at BETWEEN :start_period AND :end_period
                AND t.org_id = :org_id
                GROUP BY t.id
                """,
                {'org_id': req_user.org_id, 'start_period': start_of_this_month, 'end_period': now}
            )

        return j_response({
            "delays_per_task_type": clean_qry(qry)
        })
