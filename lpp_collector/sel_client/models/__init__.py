"""Contains all the data models used in inputs/outputs"""

from .device_grant_request import DeviceGrantRequest
from .test_case_result import TestCaseResult
from .test_case_result_passed import TestCaseResultPassed
from .test_result_request import TestResultRequest

__all__ = (
    "DeviceGrantRequest",
    "TestCaseResult",
    "TestCaseResultPassed",
    "TestResultRequest",
)
