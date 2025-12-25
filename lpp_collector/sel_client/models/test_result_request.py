from __future__ import annotations

import datetime
import json
from collections.abc import Mapping
from io import BytesIO
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field
from dateutil.parser import isoparse

from .. import types
from ..types import File

if TYPE_CHECKING:
    from ..models.test_case_result import TestCaseResult


T = TypeVar("T", bound="TestResultRequest")


@_attrs_define
class TestResultRequest:
    """
    Attributes:
        device_time (datetime.datetime):
        test_type (str):
        testcases (File):
        source_code (File):
        result (list[TestCaseResult]):
    """

    device_time: datetime.datetime
    test_type: str
    testcases: File
    source_code: File
    result: list[TestCaseResult]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        device_time = self.device_time.isoformat()

        test_type = self.test_type

        testcases = self.testcases.to_tuple()

        source_code = self.source_code.to_tuple()

        result = []
        for result_item_data in self.result:
            result_item = result_item_data.to_dict()
            result.append(result_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "deviceTime": device_time,
                "testType": test_type,
                "testcases": testcases,
                "sourceCode": source_code,
                "result": result,
            }
        )

        return field_dict

    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        files.append(("deviceTime", (None, self.device_time.isoformat().encode(), "text/plain")))

        files.append(("testType", (None, str(self.test_type).encode(), "text/plain")))

        files.append(("testcases", self.testcases.to_tuple()))

        files.append(("sourceCode", self.source_code.to_tuple()))

        for result_item_element in self.result:
            files.append(("result", (None, json.dumps(result_item_element.to_dict()).encode(), "application/json")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.test_case_result import TestCaseResult

        d = dict(src_dict)
        device_time = isoparse(d.pop("deviceTime"))

        test_type = d.pop("testType")

        testcases = File(payload=BytesIO(d.pop("testcases")))

        source_code = File(payload=BytesIO(d.pop("sourceCode")))

        result = []
        _result = d.pop("result")
        for result_item_data in _result:
            result_item = TestCaseResult.from_dict(result_item_data)

            result.append(result_item)

        test_result_request = cls(
            device_time=device_time,
            test_type=test_type,
            testcases=testcases,
            source_code=source_code,
            result=result,
        )

        test_result_request.additional_properties = d
        return test_result_request

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
