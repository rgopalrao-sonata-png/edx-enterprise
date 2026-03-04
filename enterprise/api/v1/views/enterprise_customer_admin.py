

"""
Views for `EnterpriseCustomerAdmin` model.
"""
import logging

from edx_rbac.decorators import permission_required
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404

from enterprise import models, roles_api
from enterprise.api import utils as admin_utils
from enterprise.api.v1.serializers import AdminInviteSerializer, EnterpriseCustomerAdminSerializer
from enterprise.constants import (
    ACTIVE_ADMIN_ROLE_TYPE,
    ENTERPRISE_ADMIN_ROLE,
    ENTERPRISE_CUSTOMER_PROVISIONING_ADMIN_ACCESS_PERMISSION,
    PENDING_ADMIN_ROLE_TYPE,
)

logger = logging.getLogger(__name__)

User = get_user_model()


class EnterpriseCustomerAdminPagination(PageNumberPagination):
    """
    Pagination class for EnterpriseCustomerAdmin viewset.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class EnterpriseCustomerAdminViewSet(
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API views for the ``enterprise-customer-admin`` API endpoint.
    Only allows GET, and PATCH requests.
    """
    queryset = models.EnterpriseCustomerAdmin.objects.all()
    serializer_class = EnterpriseCustomerAdminSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = EnterpriseCustomerAdminPagination

    def get_queryset(self):
        """
        Filter queryset to only show records for the admin user.
        Excludes admins whose EnterpriseCustomerUser has been deactivated.
        """
        return models.EnterpriseCustomerAdmin.objects.filter(
            enterprise_customer_user__user_fk=self.request.user,
            enterprise_customer_user__active=True,
        )

    @action(detail=True, methods=['post'])
    def complete_tour_flow(self, request, pk=None):  # pylint: disable=unused-argument
        """
        Add a completed tour flow to the admin's completed_tour_flows.
        POST /api/v1/enterprise-customer-admin/{pk}/complete_tour_flow/

        Request Arguments:
        - ``flow_uuid``: The request object containing the flow_uuid

        Returns: A response indicating success or failure
        """
        admin = self.get_object()
        flow_uuid = request.data.get('flow_uuid')

        if not flow_uuid:
            return Response(
                {'error': 'flow_uuid is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            flow = get_object_or_404(models.OnboardingFlow, uuid=flow_uuid)
            admin.completed_tour_flows.add(flow)

            return Response({
                'status': 'success',
                'message': f'Successfully added tour flow {flow.title} to completed flows'
            })

        except models.OnboardingFlow.DoesNotExist:
            return Response(
                {'error': f'OnboardingFlow with uuid {flow_uuid} does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

    @permission_required(
        ENTERPRISE_CUSTOMER_PROVISIONING_ADMIN_ACCESS_PERMISSION,
        fn=lambda request, *args, **kwargs: request.data.get('enterprise_customer_uuid'),
    )
    @action(detail=False, methods=['post'])
    def create_admin_by_email(self, request):
        """
        Create a new EnterpriseCustomerAdmin record based on an email address.
        The email address must match an existing user.

        POST /api/v1/enterprise-customer-admin/create_admin_by_email/

        The requesting user must have the ``enterprise_provisioning_admin``
        role to access this endpoint.

        Request Arguments:
        - ``email``: Email address of the user to make an admin
        - ``enterprise_customer_uuid``: UUID of the enterprise customer

        Returns: A response with the created admin record.
        """
        email = request.data.get('email')
        enterprise_customer_uuid = request.data.get('enterprise_customer_uuid')

        if not email:
            return Response(
                {'error': 'email is required'}, status=status.HTTP_400_BAD_REQUEST,
            )

        if not enterprise_customer_uuid:
            return Response(
                {'error': 'enterprise_customer_uuid is required'}, status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with email {email} does not exist'}, status=status.HTTP_404_NOT_FOUND,
            )

        try:
            enterprise_customer = models.EnterpriseCustomer.objects.get(uuid=enterprise_customer_uuid)
        except models.EnterpriseCustomer.DoesNotExist:
            return Response(
                {'error': f'EnterpriseCustomer with uuid {enterprise_customer_uuid} does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get or create EnterpriseCustomerUser
        enterprise_customer_user, _ = models.EnterpriseCustomerUser.objects.get_or_create(
            enterprise_customer=enterprise_customer,
            user_fk=user,
            defaults={'user_id': user.id}
        )

        response_status_code = status.HTTP_200_OK
        admin, was_created = models.EnterpriseCustomerAdmin.objects.get_or_create(
            enterprise_customer_user=enterprise_customer_user
        )
        if was_created:
            response_status_code = status.HTTP_201_CREATED

        roles_api.assign_admin_role(
            enterprise_customer_user.user,
            enterprise_customer=enterprise_customer_user.enterprise_customer
        )

        serializer = self.get_serializer(admin)
        return Response(serializer.data, status=response_status_code)

    @permission_required(
        ENTERPRISE_CUSTOMER_PROVISIONING_ADMIN_ACCESS_PERMISSION,
        fn=get_enterprise_uuid_for_delete_admin,
    )
    @action(
        detail=False,
        methods=['delete'],
        url_path=r'(?P<customer_id>[^/.]+)/delete'
    )
    def delete_admin(self, request, customer_id=None):
        """
        Delete an admin record based on role.

        DELETE /enterprise/api/v1/enterprise-customer-admin/{customer_id}/delete/?role=<role>

        Path Parameters:

        - ``customer_id``: ID of the admin record to delete (PendingEnterpriseCustomerAdminUser ID
          or EnterpriseCustomerUser ID)

        Query Parameters:

        - ``role``: Either 'pending' or 'admin' (required, case-insensitive)

        Based on the role query parameter:

        - If role='pending': Hard deletes PendingEnterpriseCustomerAdminUser where id=customer_id
        - If role='admin': Deletes role assignment from SystemWideEnterpriseUserRoleAssignment
          for the EnterpriseCustomerUser id=customer_id, and deactivates
          EnterpriseCustomerUser if no other roles exist

        Returns:
            200 OK with success message and user_deactivated flag (for active admins)
            400 BAD REQUEST if role parameter is missing or invalid
            404 NOT FOUND if the specified admin record doesn't exist
        """
        # Validate customer_id is a valid integer
        try:
            customer_id_int = int(customer_id)
        except (ValueError, TypeError):
            return self._error_response(
                'customer_id must be a valid integer',
                status.HTTP_400_BAD_REQUEST
            )

        role = request.query_params.get('role') or request.data.get('role')

        if not role:
            return self._error_response(
                f'role parameter is required ({PENDING_ADMIN_ROLE_TYPE} or {ACTIVE_ADMIN_ROLE_TYPE})',
                status.HTTP_400_BAD_REQUEST
            )

        role = role.lower()

        if role == PENDING_ADMIN_ROLE_TYPE:
            return self._delete_pending_admin(customer_id_int)
        elif role == ACTIVE_ADMIN_ROLE_TYPE:
            return self._delete_active_admin(customer_id_int)
        else:
            return self._error_response(
                f'Invalid role. Must be "{PENDING_ADMIN_ROLE_TYPE}" or "{ACTIVE_ADMIN_ROLE_TYPE}"',
                status.HTTP_400_BAD_REQUEST
            )

    def _error_response(self, message, status_code):
        """Helper method to create error responses."""
        return Response({'error': message}, status=status_code)

    @transaction.atomic
    def _delete_pending_admin(self, customer_id):
        """
        Delete a pending admin invitation.

        Args:
            customer_id: ID of the PendingEnterpriseCustomerAdminUser record

        Returns:
            Response object with success or error message
        """
        try:
            pending_admin = models.PendingEnterpriseCustomerAdminUser.objects.select_related(
                'enterprise_customer'
            ).get(id=customer_id)
            enterprise_customer = pending_admin.enterprise_customer
            user_email = pending_admin.user_email

            pending_admin.delete()
            logger.info(
                "Hard deleted PendingEnterpriseCustomerAdminUser id=%s for enterprise %s",
                customer_id,
                enterprise_customer.uuid
            )
            return Response(
                {'error': f'EnterpriseCustomerAdmin with id {admin_pk} does not exist'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify admin belongs to the given enterprise customer
        if admin.enterprise_customer_user.enterprise_customer_id != enterprise_customer.uuid:
            return Response(
                {'error': 'Admin does not belong to the specified enterprise customer'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Remove enterprise_admin role
        enterprise_customer_user = admin.enterprise_customer_user
        user = enterprise_customer_user.user
        roles_api.delete_admin_role_assignment(user=user, enterprise_customer=enterprise_customer)

        # Check if user has other roles for this enterprise
        has_other_roles = models.SystemWideEnterpriseUserRoleAssignment.objects.filter(
            user=user,
            enterprise_customer=enterprise_customer,
            role__name=ENTERPRISE_ADMIN_ROLE,
        )

        if not role_assignment.exists():
            return self._error_response(
                'Admin role assignment not found',
                status.HTTP_404_NOT_FOUND
            )

        # Delete the admin role
        deleted_count, _ = role_assignment.delete()
        logger.info(
            "Deleted %d admin role assignment(s) for user %s in enterprise %s",
            deleted_count,
            user.id,
            enterprise_customer.uuid
        )

        # Check if user has other roles for this enterprise with row-level locking to prevent race conditions
        has_other_roles = models.SystemWideEnterpriseUserRoleAssignment.objects.select_for_update().filter(
            user=user,
            enterprise_customer=enterprise_customer,
        ).exists()

        # Deactivate EnterpriseCustomerUser if no other roles exist (soft delete)
        user_deactivated = False
        if not has_other_roles:
            enterprise_customer_user.active = False
            enterprise_customer_user.save(update_fields=['active', 'modified'])

        return Response(status=status.HTTP_200_OK)
