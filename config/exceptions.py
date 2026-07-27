"""
config/exceptions.py

Wrap all DRF error responses in a consistent JSON envelope:
{
    "status": "error",
    "status_code": 400,
    "errors": { ... }   ← original DRF error structure
}

This makes client-side error handling predictable — every error
response has the same shape regardless of error type.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data = {
            "status": "error",
            "status_code": response.status_code,
            "errors": response.data,
        }

    return response
