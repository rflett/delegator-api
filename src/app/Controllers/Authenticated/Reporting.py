import datetime
import typing
from collections import namedtuple
from dateutil import tz

from flask import Response
from flask_restplus import Namespace

from app import session_scope, app
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions
from app.Exceptions import ProductTierLimitError
from app.Models import Subscription
from app.Models.Response import get_all_reports_response, message_response_dto


report_route = Namespace(
    path="/reporting",
    name="Reports",
    description="Returns statistics around tasks and users"
)


@report_route.route("/all")
class Reports(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @report_route.response(200, "Success", get_all_reports_response)
    @report_route.response(400, "Failed to get the reports", message_response_dto)
    def get(self, **kwargs) -> Response:
        """Returns all of the report queries """

        req_user = kwargs['req_user']

        subscription = Subscription(req_user.orgs.chargebee_subscription_id)

        if not subscription.can_get_reports():
            raise ProductTierLimitError("You cannot view reports your current plan.")

        # TODO get from request instead
        end_period = now = datetime.datetime.utcnow()
        start_period = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())  # start_of_this_month

        return self.ok({
            'trends': self._get_trends(req_user.org_id),
            'times': self._get_start_and_finish_times(req_user.org_id, start_period, end_period),
            'slowest': self._top_five_slowest_tasks(req_user.org_id, start_period, end_period),
            'time_to_start': self._average_time_to_start_a_task(req_user.org_id, start_period, end_period),
            'completed': self._completed_tasks(req_user.org_id, (start_period, end_period)),
            'priority': self._tasks_by_priority(req_user.org_id, start_period, end_period),
            'status': self._tasks_by_status(req_user.org_id, start_period, end_period),
            'delays': self._delays_per_task_type(req_user.org_id, start_period, end_period)
        })

    @staticmethod
    def _clean_qry(qry) -> list:
        """
        Takes a SQLAlchemy Query, converts named tuples to dicts, and returns a list of them.
        It also converts any SQL dates in the query to the correct date format for sending responses.

        :param qry: The query to convert to a list of dicts from named tuples
        :return:    The list of dicts
        """
        Record = namedtuple('Record', qry.keys())
        records = [dict(Record(*r)._asdict()) for r in qry.fetchall()]

        for record in records:
            for k, v in record.items():
                if type(v) == datetime.datetime:
                    record[k] = v.strftime(app.config['RESPONSE_DATE_FORMAT'])

        return records

    def _completed_tasks(self, org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
        """Return a list of completed tasks between a period for an organisation.

        :param org_id: The organisation id
        :param period: The period that the finished_at should be between
        :return:       A list of tasks that were completed between the period.
        """
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

        return self._clean_qry(qry)

    def _delayed_tasks(self, org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
        """Return a list of tasks that were delayed in a period

        :param org_id: The organisation id
        :param period: The period that delayed_at should be between
        :return:       A list of delayed tasks
        """
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

        return self._clean_qry(qry)

    def _dropped_tasks(self, org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
        """Return a list of tasks that were dropped in a period

        :param org_id: The organisation id
        :param period: The period in which tasks were dropped_at
        :return:       A list of dropped tasks
        """
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

        return self._clean_qry(qry)

    def _tasks_created(self, org_id: int, period: typing.Tuple[datetime.datetime, datetime.datetime]) -> list:
        """Return a list of tasks that were created between a period.

        :param org_id: The organisation id
        :param period: The period in which the task was created
        :return:       A list of tasks
        """
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

        return self._clean_qry(qry)

    def _get_trends(self, org_id) -> list:
        """
        Return a list of tasks that were created, completed, delayed and dropped, within several periods.
        The different periods that this is calcuated is 'today', 'yesterday', 'since the start of this week' and 'since
        the start of this month'

        :param org_id: The organisation id
        :return:       A list of counts of the number of tasks in different states
        """
        # get the time right now
        now = datetime.datetime.utcnow()
        # get the time for the start of today
        start_of_today = datetime.datetime(now.year, now.month, now.day, tzinfo=tz.tzutc())
        # get the time of the start of yesterday
        yesterday = now - datetime.timedelta(
            days=1,
            hours=now.hour,
            minutes=now.minute,
            seconds=now.second,
            microseconds=now.microsecond
        )
        # get the time for the start of this week
        start_of_this_week = start_of_today - datetime.timedelta(days=now.weekday())
        # get the time for the start of the month
        start_of_this_month = datetime.datetime(now.year, now.month, 1, tzinfo=tz.tzutc())

        # return object
        reports = []

        # each dict item of the return list, created, completed, delayed and dropped tasks
        # this is a dict with the key being the 'trend' and the value being the function that calculates the trend
        trends = {
            "Created": self._tasks_created,
            "Completed": self._completed_tasks,
            "Delayed": self._delayed_tasks,
            "Dropped": self._dropped_tasks
        }
        # dict of times as calculated earlier
        times = {
            "today": start_of_today,
            "yesterday": yesterday,
            "this_week": start_of_this_week,
            "this_month": start_of_this_month
        }
        # for each trend, get the count of tasks in each 'category' for each 'time period'
        for title, func in trends.items():
            trend = {"title": title}
            for period, _date in times.items():
                trend[period] = len(func(org_id, (_date, now)))
            reports.append(trend)

        return reports

    def _get_start_and_finish_times(
            self,
            org_id: int,
            start_period: datetime.datetime, end_period: datetime.datetime) -> list:
        """Get time to start and time to finish for tasks """
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

        return self._clean_qry(qry)

    def _top_five_slowest_tasks(
            self,
            org_id: int,
            start_period: datetime.datetime, end_period: datetime.datetime) -> list:
        """Get the 5 tasks with longest time to finish """
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

        return self._clean_qry(qry)

    @staticmethod
    def _average_time_to_start_a_task(
            org_id: int,
            start_period: datetime.datetime,
            end_period: datetime.datetime) -> int:
        """Get the average time to start a task """
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

    def _tasks_by_priority(self, org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
        """Get a list of tasks grouped by their priority"""
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

        return self._clean_qry(qry)

    def _tasks_by_status(self, org_id: int, start_period: datetime.datetime, end_period: datetime.datetime) -> list:
        """Get a list of tasks grouped by their status """
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

        return self._clean_qry(qry)

    def _delays_per_task_type(
            self,
            org_id: int,
            start_period: datetime.datetime,
            end_period: datetime.datetime) -> list:
        """
        Calculate the amount of delay that each task has had. This just querys the total delay time for each task - not
        if it was actually resumed before the delay period finished. It's an upper bound - not the exact delay period.
         """
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

        return self._clean_qry(qry)