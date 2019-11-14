import copy

from flask import Response, request
from flask_restplus import Namespace
from sqlalchemy import and_

from app import session_scope
from app.Controllers.Base import RequestValidationController
from app.Decorators import requires_jwt, handle_exceptions, authorize
from app.Models import TaskLabel
from app.Models.Enums import Operations, Resources
from app.Models.Response import task_labels_response

task_labels_route = Namespace(
    path="/task-labels",
    name="Tasks Labels",
    description="Manage Task Labels"
)


@task_labels_route.route('/')
class TaskLabels(RequestValidationController):

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.GET, Resources.TASK_LABELS)
    @task_labels_route.response(200, "Success", task_labels_response)
    def get(self, **kwargs) -> Response:
        """Returns all task labels """
        req_user = kwargs['req_user']

        with session_scope() as session:
            task_labels_qry = session.query(TaskLabel).filter_by(org_id=req_user.org_id).all()

        req_user.log(
            operation=Operations.GET,
            resource=Resources.TASK_LABELS
        )
        return self.ok({'labels': [tl.as_dict() for tl in task_labels_qry]})

    @handle_exceptions
    @requires_jwt
    @authorize(Operations.UPDATE, Resources.TASK_LABELS)
    @task_labels_route.expect(task_labels_response)
    @task_labels_route.response(200, "Success", task_labels_response)
    def post(self, **kwargs) -> Response:
        """Creates and deletes task labels"""
        req_user = kwargs['req_user']
        request_body = request.get_json()

        request_labels = self.validate_update_task_labels_request(request_body)
        new_labels = copy.deepcopy(request_labels)

        # delete labels from db that are not in the incoming request
        with session_scope() as session:
            session.query(TaskLabel) \
                .filter(
                    and_(
                        ~TaskLabel.id.in_([l['id'] for l in request_labels if l.get('id') is not None]),
                        TaskLabel.org_id == req_user.org_id
                    )
                ).delete(synchronize_session=False)

        # find labels to update
        with session_scope() as session:
            labels_to_update_qry = session.query(TaskLabel) \
                .filter(
                    and_(
                        TaskLabel.id.in_([l['id'] for l in request_labels if l.get('id') is not None]),
                        TaskLabel.org_id == req_user.org_id
                    )
                ).all()
            for l in labels_to_update_qry:
                for rl in request_labels:
                    if l.id == rl.get('id'):
                        l.label = rl['label']
                        l.colour = rl['colour']
                        new_labels.remove(rl)

        # create new, the ones that were updated were removed from the request_labels list
        with session_scope() as session:
            for l in new_labels:
                new_label = TaskLabel(label=l['label'], colour=l['colour'], org_id=req_user.org_id)
                session.add(new_label)

        # get all labels to return
        with session_scope() as session:
            task_labels_qry = session.query(TaskLabel).filter_by(org_id=req_user.org_id).all()

        req_user.log(
            operation=Operations.UPDATE,
            resource=Resources.TASK_LABELS
        )
        return self.ok({'labels': [tl.as_dict() for tl in task_labels_qry]})
