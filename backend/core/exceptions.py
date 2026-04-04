import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import PermissionDenied
from django.http import Http404

logger = logging.getLogger(__name__)

def get_first_matching_attr(obj, *attrs, default=None):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)
    return default

def api_exception_handler(exc, context):
    """
    Custom exception handler for Django Rest Framework that adds a standard
    format suited for frontend toast notifications.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If response is None, it means it's not a standard DRF exception (e.g. 500 Error, KeyError)
    if response is None:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        if isinstance(exc, Http404):
            response = Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        elif isinstance(exc, PermissionDenied):
            response = Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response(
                {
                    "error": True,
                    "message": "An unexpected server error occurred.",
                    "toast_type": "error",
                    "details": str(exc)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # Determine message from response.data if it exists
    error_message = "An error occurred."
    toast_type = "error"
    
    if type(response.data) is dict:
        # Check standard DRF keys
        if 'detail' in response.data:
            error_message = str(response.data['detail'])
        elif 'non_field_errors' in response.data:
            error_message = str(response.data['non_field_errors'][0])
        else:
            # It's likely a field validation error. Use the first one.
            first_key = next(iter(response.data))
            field_error = response.data[first_key]
            
            if isinstance(field_error, list) and len(field_error) > 0:
                error_message = f"{first_key.replace('_', ' ').title()}: {field_error[0]}"
            elif isinstance(field_error, str):
                error_message = f"{first_key.replace('_', ' ').title()}: {field_error}"
            else:
                error_message = f"Validation error on field: {first_key}"
                
        # Status code checking for toast type
        if response.status_code >= 500:
            toast_type = "error"
        elif response.status_code >= 400:
            if response.status_code in [401, 403]:
                toast_type = "warning"
            else:
                toast_type = "error"

    elif type(response.data) is list:
        if len(response.data) > 0:
            error_message = str(response.data[0])

    original_details = response.data

    # Standardize the output
    response.data = {
        "error": True,
        "message": error_message,
        "toast_type": toast_type,
        "details": original_details
    }

    return response
