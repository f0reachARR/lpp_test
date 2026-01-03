# Consent state management

import os
import sys

from lpp_collector.docker import fix_permission, run_test_container, update
from .config import (
    IS_DOCKER_ENV,
    LPP_AFTER_CONSENT_TEXT,
    LPP_BASE_URL,
    LPP_DATA_DIR,
    LPP_CONSENT_TEXT,
    LPP_REVOKE_CONSENT_TEXT,
)
from json import load, dump

try:
    from typing import TypedDict, Optional
except ImportError:
    from typing_extensions import TypedDict, Optional
from whiptail import Whiptail
from .sel_client import Client
from .sel_client.api.default import (
    delete_api_device_device_id,
    post_api_device_device_id,
)

LPP_DEVICE_FILE = os.path.join(LPP_DATA_DIR, "device.json")


class DeviceData(TypedDict):
    device_id: str


class LppDevice:
    def __init__(self):
        self._device: Optional[DeviceData] = None
        try:
            if os.path.exists(LPP_DEVICE_FILE):
                with open(LPP_DEVICE_FILE, "r") as f:
                    self._device = load(f)
            else:
                import uuid

                self._device = DeviceData(device_id=str(uuid.uuid4()))
                self.save_device(self._device)
        except Exception as e:
            print(f"Failed to load device information (unexpected error): {e}")

    def get_device(self):
        return self._device

    def save_device(self, device: DeviceData):
        self._device = device
        try:
            with open(LPP_DEVICE_FILE, "w") as f:
                dump(device, f)
        except Exception as e:
            print(f"Failed to save device information (unexpected error): {e}")

    def delete_device(self):
        self._device = None
        os.remove(LPP_DEVICE_FILE)


def show_consent():
    consent_info = LppDevice()
    current_device = consent_info.get_device()

    whiptail = Whiptail(title="Consent Form for experiment")
    client = Client(LPP_BASE_URL)

    if current_device is not None:
        consent = whiptail.run(
            "yesno",
            LPP_REVOKE_CONSENT_TEXT,
            extra_args=[
                "--scrolltext",
                "--yes-button",
                "同意を取り消す",
                "--no-button",
                "キャンセル",
            ],
        )

        if consent.returncode == 1:
            # Cancelled
            return

        try:
            response = delete_api_device_device_id.sync_detailed(
                current_device["device_id"],
                client=client,
            )
            if response is None:
                print("同意情報の取り消しに失敗しました")
                return
            print("同意情報を取り消しました")
        except Exception as e:
            print(f"同意情報の取り消しに失敗しました: {e}")

        return

    # Ask for consent using whiptail
    consent = whiptail.run(
        "yesno",
        LPP_CONSENT_TEXT,
        extra_args=[
            "--scrolltext",
            "--yes-button",
            "同意する",
            "--no-button",
            "同意しない",
        ],
    )

    if consent.returncode == 1:
        # Rejected
        return

    try:
        response = post_api_device_device_id.sync_detailed(
            client=client, device_id=current_device["device_id"]
        )
        if response is None:
            print("同意情報の送信に失敗しました")
            return
        url = response.consent_form_url
        print(LPP_AFTER_CONSENT_TEXT.format(form_url=url))

        consent_info.save_device({"device_id": response.device_id})

    except Exception as e:
        print(f"同意情報の送信に失敗しました: {e}")


def main():
    if IS_DOCKER_ENV:
        show_consent()
    else:
        update()
        run_test_container(["lppconsent", *sys.argv[1:]])

    if IS_DOCKER_ENV:
        # Fix permissions
        fix_permission()
