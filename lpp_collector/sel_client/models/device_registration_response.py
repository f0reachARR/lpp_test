from typing import Any, Dict, Type, TypeVar, Tuple, Optional, BinaryIO, TextIO, TYPE_CHECKING

from typing import List


from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset







T = TypeVar("T", bound="DeviceRegistrationResponse")


@_attrs_define
class DeviceRegistrationResponse:
    """ 
        Attributes:
            device_id (str):
            consent_form_url (str):
     """

    device_id: str
    consent_form_url: str
    additional_properties: Dict[str, Any] = _attrs_field(init=False, factory=dict)


    def to_dict(self) -> Dict[str, Any]:
        device_id = self.device_id

        consent_form_url = self.consent_form_url


        field_dict: Dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "deviceId": device_id,
            "consentFormUrl": consent_form_url,
        })

        return field_dict



    @classmethod
    def from_dict(cls: Type[T], src_dict: Dict[str, Any]) -> T:
        d = src_dict.copy()
        device_id = d.pop("deviceId")

        consent_form_url = d.pop("consentFormUrl")

        device_registration_response = cls(
            device_id=device_id,
            consent_form_url=consent_form_url,
        )


        device_registration_response.additional_properties = d
        return device_registration_response

    @property
    def additional_keys(self) -> List[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
