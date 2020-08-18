import datetime
import typing

import structlog
from marshmallow import Schema, fields, ValidationError
from sqlalchemy import or_, func

from app.Models.Enums import TaskStatuses
from app.Models.Dao import Task, TaskLabel

log = structlog.getLogger()


def _validate_str_list(s: str):
    """Parses a string containing comma separated ints and ensures they're all ints"""
    # try and split into list
    items = s.split(",")
    if len(items) == 0:
        # ok
        return
    if len(s.strip()) == 0:
        # ok
        return
    for i in items:
        try:
            _ = int(i)
        except ValueError:
            raise ValidationError(f"'{i}' is not an integer")


def _validate_status(s: str):
    """Parses a string containing comma separated ints and ensures they're all valid statuses"""
    # try and split into list
    items = s.split(",")
    if len(items) == 0:
        # ok
        return
    if len(s.strip()) == 0:
        # ok
        return
    for i in items:
        if i not in TaskStatuses.all:
            raise ValidationError(f"{i} is not a valid status")


class GetTasksFiltersSchema(Schema):
    """The schema for validating query parameters on the request"""

    assignee = fields.Str(validate=_validate_str_list)
    created_by = fields.Str(validate=_validate_str_list)
    status = fields.Str(validate=_validate_status)
    priority = fields.Str(validate=_validate_str_list)
    labels = fields.Str(validate=_validate_str_list)
    from_date = fields.Date(format="%Y-%m-%dT%H:%M:%S.%f")
    to_date = fields.Date(format="%Y-%m-%dT%H:%M:%S.%f")


class GetTasksFilters(object):
    def __init__(self, dto: dict):
        """
        Create the object
        :param dto: A request.args object
        """
        self.assignee = self._get_ints_from_strlist(dto.get("assignee"))
        self.created_by = self._get_ints_from_strlist(dto.get("created_by"))
        self.priority = self._get_ints_from_strlist(dto.get("priority"), 0, 2)
        self.labels = self._get_ints_from_strlist(dto.get("labels"), 1)

        try:
            self.status = dto.get("status").split(",")
        except AttributeError:
            self.status = None

        from_date = dto.get("from_date")
        if from_date is not None:
            self.from_date = datetime.datetime.strptime(from_date, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            self.from_date = None

        to_date = dto.get("to_date")
        if to_date is not None:
            self.to_date = datetime.datetime.strptime(to_date, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            self.to_date = None

    def __repr__(self):
        """Returns a str repr of the filters"""
        fd = self.from_date.strftime("%Y-%m-%d %H:%M:%S") if self.from_date is not None else None
        td = self.to_date.strftime("%Y-%m-%d %H:%M:%S") if self.to_date is not None else None
        return (
            f"assignee={self.assignee}, "
            f"createdBy={self.created_by}, "
            f"priority={self.priority}, "
            f"labels={self.labels}, "
            f"status={self.status}, "
            f"fromDate={fd}, "
            f"toDate={td}"
        )

    def filters(self, org_id: int, label1: TaskLabel, label2: TaskLabel, label3: TaskLabel) -> list:
        """Returns a list of sqlalchemy filters to be added to a query"""
        # filter things
        filters = [Task.org_id == org_id]

        # filter by assignee
        if self.assignee is not None:
            filters.append(Task.assignee.in_(self.assignee))

        # filter by created by
        if self.created_by is not None:
            filters.append(Task.created_by.in_(self.created_by))

        # filter by priority
        if self.priority is not None:
            filters.append(Task.priority.in_(self.priority))

        # filter by status
        if self.status is not None:
            filters.append(Task.status.in_(self.status))

        # filter by labels
        if self.labels is not None:
            for label_id in self.labels:
                filters.append(or_(label1.id == label_id, label2.id == label_id, label3.id == label_id))

        # filter from date
        if self.from_date is not None:
            filters.append(Task.created_at >= self.from_date)

        # filter to date
        if self.to_date is not None:
            filters.append(func.coalesce(Task.finished_at, Task.created_at) <= self.to_date)

        log.info(f"Parsed {len(filters)} filters")
        return filters

    @staticmethod
    def _get_ints_from_strlist(s: str, _min: int = None, _max: int = None) -> typing.Union[typing.List[int], None]:
        """ Given comma separated integers in a string, return them as a list
        :param s: The str containing comma separated ints, e.g. 1,2,3
        :param _min: Integers in the string less than the min are not returned
        :param _max: Integers in the string greater than the min are not returned
        :return: A list of ints or None if no ints meet validation criteria
        """
        if s is None or not isinstance(s, str):
            return None
        items = s.split(",")
        if len(items) == 0:
            return None

        ret = []
        for i in items:
            if len(i.strip()) == 0:
                continue
            try:
                item = int(i)
            except ValueError:
                continue
            if _min is not None and item < _min:
                continue
            if _max is not None and item > _max:
                continue
            ret.append(item)

        if len(ret) == 0:
            return None

        return ret
