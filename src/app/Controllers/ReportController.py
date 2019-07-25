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
            SELECT u.first_name || ' ' || u.last_name AS finished_by,
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
            SELECT u.first_name || ' ' || u.last_name AS delayed_by,
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


def get_trends(org_id) -> list:
    """ Get completed tasks """
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
    trends = {
        "Created": tasks_created,
        "Completed": completed_tasks,
        "Delayed": delayed_tasks,
        "Dropped": dropped_tasks
    }
    times = {
        "today": start_of_today,
        "yesterday": yesterday,
        "this_week": start_of_this_week,
        "this_month": start_of_this_month
    }
    for title, func in trends.items():
        trend = {"title": title}
        for period, _date in times.items():
            trend[period] = len(func(org_id, (_date, now)))
        reports.append(trend)

    return reports


def get_start_and_finish_times(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
    """ Get time to start and time to finish for tasks """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT tt.label AS task_type,
                   AVG(EXTRACT(EPOCH FROM (t.started_at - t.created_at))) AS time_to_start,
                   AVG(EXTRACT(EPOCH FROM (t.finished_at - t.created_at))) AS time_to_finish
            FROM tasks t INNER JOIN task_types tt
                         ON t.type = tt.id
            WHERE t.created_at BETWEEN :start_period AND :end_period
            AND t.started_at BETWEEN :start_period AND :end_period OR t.started_at IS NULL
            AND t.finished_at BETWEEN :start_period AND :end_period OR t.finished_at IS NULL
            AND t.org_id = :org_id
            GROUP BY tt.label
            ORDER BY time_to_finish DESC
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def top_five_slowest_tasks(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
    """ Get the 5 tasks with longest time to finish """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT t.id AS task_id,
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
            GROUP BY 1, 2, 3
            ORDER BY time_to_finish DESC
            LIMIT 5
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def average_time_to_start_a_task(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> int:
    """ Get the average time to start a task """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT AVG(EXTRACT(EPOCH FROM (t.started_at - t.created_at))) AS time_to_start
            FROM tasks t
            WHERE t.created_at BETWEEN :start_period AND :end_period
            AND t.started_at BETWEEN :start_period AND :end_period
            AND t.org_id = :org_id
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        ).first()

    return qry.time_to_start


def tasks_by_priority(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
    """ Get the average time to start a task """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.first_name || ' ' || u.last_name AS assignee,
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
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def tasks_by_status(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
    """ Get the average time to start a task """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT u.first_name || ' ' || u.last_name AS assignee,
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
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


def delays_per_task_type(org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
    """ Get time to start and time to finish for tasks """
    with session_scope() as session:
        qry = session.execute(
            """
            SELECT tt.label AS task_type,
                   SUM(td.delay_for) AS delayed_for
            FROM tasks_delayed td INNER JOIN tasks t
                                  ON td.task_id = t.id
                                  INNER JOIN task_types tt
                                  ON t.type = tt.id
            WHERE td.delayed_at BETWEEN :start_period AND :end_period
            AND t.org_id = :org_id
            GROUP BY tt.label
            """,
            {'org_id': org_id, 'start_period': start_period, 'end_period': end_period}
        )

    return clean_qry(qry)


class ReportController(object):
    @staticmethod
    def get_all(req: request) -> Response:
        """ Get time to start and time to finish for tasks """

        req_user = AuthenticationController.get_user_from_request(req.headers)

        AuthorizationController.authorize_request(
            auth_user=req_user,
            operation=Operations.GET,
            resource=Resources.REPORTS_PAGE
        )

        # TODO get from request instead
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        return j_response({
            'trends': get_trends(req_user.org_id),
            'times': get_start_and_finish_times(req_user.org_id, start_period, end_period),
            'slowest': top_five_slowest_tasks(req_user.org_id, start_period, end_period),
            'time_to_start': average_time_to_start_a_task(req_user.org_id, start_period, end_period),
            'completed': completed_tasks(req_user.org_id, (start_period, end_period)),
            'priority': tasks_by_priority(req_user.org_id, start_period, end_period),
            'status': tasks_by_status(req_user.org_id, start_period, end_period),
            'delays': delays_per_task_type(req_user.org_id, start_period, end_period)
        })
