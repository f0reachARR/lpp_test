from pathlib import Path
from lpp_collector.config import LPP_BASE_URL, LPP_DATA_DIR, LPP_SOURCE_FILES
from lpp_collector.sel_client.models.test_case_result import TestCaseResult
from lpp_collector.sel_client.models.test_case_result_passed import TestCaseResultPassed
from lpp_collector.sel_client.types import File
from .sel_client.client import Client
from .sel_client.api.default import post_api_testresult_device_id
from .sel_client.models import TestResultRequest
from glob import glob
from _pytest.reports import TestReport
import tarfile
from io import BytesIO
from datetime import datetime
from pickle import load, dump
from httpx import Timeout
import threading


class Uploader:
    def __init__(self, device_id: str):
        self.client = Client(base_url=LPP_BASE_URL, timeout=Timeout(3))
        self.device_id = device_id
        self.test_results: list[TestCaseResult] = []
        self.test_queue_dir = Path(LPP_DATA_DIR) / "upload_queue"
        self.stop_retry = threading.Event()
        self.retry_thread = None
        self.retry_success = True  # Track if background retry succeeded

    def add_test_result(self, report: TestReport):
        self.test_results.append(
            TestCaseResult(
                name=report.nodeid,
                passed=(
                    TestCaseResultPassed.PASSED
                    if report.passed
                    else TestCaseResultPassed.FAILED
                ),
                message=report.longreprtext,
            )
        )

    def has_any_test_result(self):
        return len(self.test_results) > 0

    def _compress_tar(self, files) -> BytesIO:
        tar = BytesIO()
        with tarfile.open(fileobj=tar, mode="w") as tf:
            for file in files:
                tf.add(file)
        return tar

    def _store_test_result(self, test_result: TestResultRequest):
        filename = f"{datetime.now().timestamp()}.dat"
        self.test_queue_dir.mkdir(parents=True, exist_ok=True)
        test_result_file = self.test_queue_dir / filename
        with open(test_result_file, "wb") as f:
            dump(test_result, f)

    def start_background_retry(self):
        """Start background thread to retry failed uploads"""
        if self.retry_thread is None or not self.retry_thread.is_alive():
            self.stop_retry.clear()
            self.retry_success = True  # Reset success flag
            self.retry_thread = threading.Thread(target=self._background_retry_wrapper, daemon=True)
            self.retry_thread.start()

    def _background_retry_wrapper(self):
        """Wrapper to capture _flush_test_queue result"""
        self.retry_success = self._flush_test_queue()

    def _flush_test_queue(self) -> bool:
        files = list(self.test_queue_dir.glob("*.dat")) if self.test_queue_dir.exists() else []
        for file in files:
            # Check if we should stop
            if self.stop_retry.is_set():
                return True
            
            with open(file, "rb") as f:
                test_result = load(f)
            try:
                response = post_api_testresult_device_id.sync_detailed(
                    device_id=self.device_id, client=self.client, body=test_result
                )

                if response.status_code != 201:
                    raise Exception(
                        f"Failed to upload test results: {response.content}"
                    )

                file.unlink()

            except Exception as e:
                # 1件でもアップロードに失敗した場合は、次回アップロード時に再度アップロードを試みる
                return False
        return True

    def store(self, source_dir: str, test_type: str):
        source_files = sum(
            [
                glob(f"{source_dir}/**/{pat}", recursive=True)
                for pat in LPP_SOURCE_FILES
            ],
            [],
        )

        source_blob = self._compress_tar(source_files)
        source_blob.seek(0)

        result = TestResultRequest(
            device_time=datetime.now(),
            test_type=test_type,
            result=self.test_results,
            testcases=File(payload=BytesIO(), file_name="source.tar"),
            source_code=File(payload=source_blob, file_name="source.tar"),
        )

        self._store_test_result(result)

    def upload(self, source_dir: str, test_dir: str, test_type: str):
        # Stop background retry thread if running
        self.stop_retry.set()
        if self.retry_thread and self.retry_thread.is_alive():
            self.retry_thread.join(timeout=0.5)  # Wait briefly for thread to stop
        
        # If background retry failed, skip upload and store for later
        can_upload = self.retry_success

        # Find source code files
        source_files = sum(
            [
                glob(f"{source_dir}/**/{pat}", recursive=True)
                for pat in LPP_SOURCE_FILES
            ],
            [],
        )

        source_blob = self._compress_tar(source_files)
        source_blob.seek(0)

        result = TestResultRequest(
            device_time=datetime.now(),
            test_type=test_type,
            result=self.test_results,
            testcases=File(payload=BytesIO(), file_name="source.tar"),
            source_code=File(payload=source_blob, file_name="source.tar"),
        )

        # Upload test result
        try:
            if not can_upload:
                raise Exception("Background retry failed, skipping upload")
            
            response = post_api_testresult_device_id.sync_detailed(
                device_id=self.device_id, client=self.client, body=result
            )

            if response.status_code != 201:
                raise Exception(f"Failed to upload test results: {response.content}")
        except:
            self._store_test_result(result)
            return
