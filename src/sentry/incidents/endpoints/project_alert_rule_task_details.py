from django.http import Http404
from rest_framework.request import Request
from rest_framework.response import Response

from sentry.api.api_owners import ApiOwner
from sentry.api.api_publish_status import ApiPublishStatus
from sentry.api.base import region_silo_endpoint
from sentry.api.bases.project import ProjectEndpoint, ProjectSettingPermission
from sentry.api.serializers import serialize
from sentry.incidents.models import AlertRule
from sentry.integrations.slack.utils import RedisRuleStatus


@region_silo_endpoint
class ProjectAlertRuleTaskDetailsEndpoint(ProjectEndpoint):
    owner = ApiOwner.ISSUES
    publish_status = {
        "GET": ApiPublishStatus.PRIVATE,
    }
    permission_classes = (ProjectSettingPermission,)

    def get(self, request: Request, project, task_uuid) -> Response:
        """
        Retrieve the status of the async task

        Return details of the alert rule if the task is successful

        """
        client = RedisRuleStatus(task_uuid)
        result = client.get_value()

        status = result["status"]
        rule_id = result.get("rule_id")
        error = result.get("error")

        # if the status is "pending" we don't have a rule yet or error
        context = {"status": status, "alertRule": None, "error": None}

        if rule_id and status == "success":
            try:
                alert_rule = AlertRule.objects.get(
                    snuba_query__subscriptions__project=project, id=rule_id
                )
                context["alertRule"] = serialize(alert_rule, request.user)
            except AlertRule.DoesNotExist:
                raise Http404
        if status == "failed":
            context["error"] = error

        return Response(context, status=200)
