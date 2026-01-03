from _pytest.config import Config
from _pytest.reports import TestReport

from lpp_collector.config import TARGETPATH

from .uploader import Uploader
from .consent import LppDevice


class LppCollector:
    def __init__(self, config: Config):
        self.consent = LppDevice()
        self.uploader = Uploader(device_id="test_device_id")
        if self.consent.get_device() is not None:
            self.uploader.device_id = self.consent.get_device()["device_id"]
        # Start background retry of failed uploads
        self.uploader.start_background_retry()

    def pytest_runtest_logreport(self, report: TestReport):
        if report.when == "call":
            self.uploader.add_test_result(report)

    def pytest_sessionfinish(self, session, exitstatus):
        if self.consent.get_device() is None:
            self.uploader.store(source_dir=TARGETPATH, test_type="")
            return

        test_type = ""

        self.uploader.device_id = self.consent.get_device()["device_id"]
        self.uploader.upload(source_dir=TARGETPATH, test_dir=".", test_type=test_type)


def pytest_configure(config: Config):  # pragma: no cover
    config.pluginmanager.register(LppCollector(config))
