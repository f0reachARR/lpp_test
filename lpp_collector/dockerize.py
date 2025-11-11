from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import subprocess
from typing import List, Literal
import pickle
import base64
import os
import tempfile


@dataclass
class DockerizeMountPoint:
    host_path: str
    container_path: str


class DockerizeConfiguration:
    def __init__(
        self,
        image_name: str,
        update_marker: str,
        update_interval_seconds: int = 3600,
        mount_points: List[DockerizeMountPoint] = [],
        build_per_execute=False,
        build_context="",
        default_cwd: str | None = None,
    ):
        self.image_name = image_name
        self.update_marker = Path(update_marker).expanduser()
        self.update_interval_seconds = update_interval_seconds
        self.build_per_execute = build_per_execute
        self.build_context = build_context
        self.mount_points = mount_points
        self.default_cwd = default_cwd

        # Constant values
        self.should_fix_permission = not os.name == "nt"
        self.permission_uid = os.getuid() if self.should_fix_permission else None
        self.permission_gid = os.getgid() if self.should_fix_permission else None

    @staticmethod
    def default():
        import os

        image_name = (
            os.environ["LPP_DOCKER_IMAGE"]
            if "LPP_DOCKER_IMAGE" in os.environ
            else "ghcr.io/f0reacharr/lpp_test:latest"
        )
        update_marker = "~/.config/lpp/.dockerize_update_marker"
        build_context = os.environ["LPP_DOCKER_CONTEXT"]
        build_per_execute = build_context is not None

        configuration = DockerizeConfiguration(
            image_name=image_name,
            update_marker=update_marker,
            update_interval_seconds=3600,
            build_per_execute=build_per_execute,
            build_context=build_context,
            mount_points=[
                DockerizeMountPoint(
                    host_path=os.path.expanduser("~/.config/lpp"),
                    container_path="/lpp/data",
                ),
                DockerizeMountPoint(
                    host_path=os.getcwd(),
                    container_path="/workspaces",
                ),
            ],
            default_cwd="/workspaces",
        )
        return configuration

    def with_mount_point(self, host_path: str, container_path: str | None = None):
        self.mount_points.append(
            DockerizeMountPoint(
                host_path=host_path, container_path=container_path or host_path
            )
        )
        return self


class Dockerize:
    def __init__(self, configuration: DockerizeConfiguration | None):
        self.configuration = (
            configuration
            if configuration is not None
            else DockerizeConfiguration.default()
        )

    def _get_image_id(self) -> str | None:
        try:
            result = subprocess.run(
                ["docker", "images", "-q", f"{self.configuration.image_name}"],
                capture_output=True,
                text=True,
                check=True,
            )
            image_id = result.stdout.strip()
            return image_id if image_id else None
        except subprocess.CalledProcessError:
            return None

    def _execute_command(
        self, cmd: List[str], raise_error=False, error_reason: str | None = None
    ) -> bool:
        try:
            subprocess.run(cmd, check=True)
            return True
        except subprocess.CalledProcessError:
            if raise_error:
                raise RuntimeError(
                    error_reason
                    if error_reason is not None
                    else f"{' '.join(cmd)} failed"
                )
            return False

    def _build_image(self) -> bool:
        return self._execute_command(
            [
                "docker",
                "buildx",
                "build",
                "-t",
                self.configuration.image_name,
                self.configuration.build_context,
            ],
            raise_error=True,
            error_reason="Image build failed",
        )

    def _pull_image(self) -> bool:
        return self._execute_command(
            [
                "docker",
                "pull",
                self.configuration.image_name,
            ],
            raise_error=True,
        )

    def _remove_image(self, image_id: str) -> bool:
        return self._execute_command(["docker", "rmi", image_id])

    def _write_update_marker(self):
        self.configuration.update_marker.touch()

    def _check_update(self) -> Literal["first", "older", "newer"]:
        if not self.configuration.update_marker.exists():
            return "first"

        last_update = self.configuration.update_marker.stat().st_mtime

        import time

        now = time.time()
        if (now - last_update) > self.configuration.update_interval_seconds:
            return "older"

        return "newer"

    def update_image(self):
        if self.configuration.build_per_execute:
            self._build_image()
            return

        if self._check_update() == "newer":
            return

        previous_image_id = self._get_image_id()
        self._pull_image()
        current_image_id = self._get_image_id()

        if previous_image_id != current_image_id and previous_image_id is not None:
            self._remove_image(previous_image_id)

        self._write_update_marker()

    def run(
        self,
        cmd: List[str],
        temporary_mounts: List[DockerizeMountPoint] = [],
        env: dict = {},
        pwd: str | None = None,
    ):
        mount_args = sum(
            [
                [
                    "-v",
                    f"{mount_point.host_path}:{mount_point.container_path}",
                ]
                for mount_point in self.configuration.mount_points + temporary_mounts
            ],
            [],
        )
        env_args = sum([["-e", f"{key}={value}"] for key, value in env.items()], [])
        pwd = pwd or self.configuration.default_cwd
        pwd_args = ["-w", pwd] if pwd else []
        run_args = [
            "run",
            "-it",
            "--rm",
            *mount_args,
            *env_args,
            *pwd_args,
            self.configuration.image_name,
            *cmd,
        ]

        # Run Docker container
        subprocess.call(["docker", *run_args])

    def wrap(self, func):
        import functools

        if hasattr(func, "__dockerized__"):
            return func

        func.__dockerized__ = True

        @functools.wraps(func)
        def _wrapper(*args, **keywords):
            self.update_image()

            print(
                f"Dispatching to Dockerized environment ({func.__module__}.{func.__qualname__})"
            )

            parameters_binary = pickle.dumps(
                [func.__module__, func.__qualname__, args, keywords, self.configuration]
            )
            base64_parameters = base64.b64encode(parameters_binary).decode()

            print(
                f"Serialized parameters size: {len(base64_parameters)} bytes / {args}"
            )

            code = ";".join(
                [
                    "from lpp_collector.dockerize import dedockerize",
                    f"dedockerize('{base64_parameters}')",
                ]
            )

            output_path = "/tmp/lpp_dockerize_output.txt"
            tmp_file = tempfile.NamedTemporaryFile(delete=False)
            tmp_file.close()

            self.run(
                ["python3", "-c", code],
                temporary_mounts=[
                    DockerizeMountPoint(
                        host_path=tmp_file.name,
                        container_path=output_path,
                    )
                ],
                env={"LPP_DOCKERIZE_OUTPUT_PATH": output_path},
            )

            with open(tmp_file.name, "r") as f:
                result_b64 = f.read()

            result_binary = base64.b64decode(result_b64.encode())
            result = pickle.loads(result_binary)
            os.unlink(tmp_file.name)
            return result

        return _wrapper


def dedockerize(input: str):
    import pickle
    from base64 import b64decode, b64encode

    result = None
    try:
        decoded = b64decode(input.encode())
        [mod, qualname, args, keywords, config] = pickle.loads(decoded)
        func = __import__(mod, fromlist=[qualname])
        for attr in qualname.split("."):
            func = getattr(func, attr)
        print(f"Running in Dockerized environment ({mod}.{qualname})")
        result = func(*args, **keywords)

        if isinstance(config, DockerizeConfiguration) and config.should_fix_permission:
            mount_points = config.mount_points
            for mount_point in mount_points:
                host_path = mount_point.host_path
                if not os.path.exists(host_path):
                    continue
                subprocess.call(
                    [
                        "chown",
                        "-R",
                        f"{config.permission_uid}:{config.permission_gid}",
                        host_path,
                    ]
                )

    except Exception as e:
        result = e
    finally:
        result_binary = pickle.dumps(result)
        result_b64 = b64encode(result_binary).decode()
        if os.environ.get("LPP_DOCKERIZE_OUTPUT_PATH"):
            with open(os.environ["LPP_DOCKERIZE_OUTPUT_PATH"], "w") as f:
                f.write(result_b64)
