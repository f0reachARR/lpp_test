import subprocess


class Dockerize:
    def __init__(self, image_name: str, tag: str = "latest"):
        self.image_name = image_name
        self.tag = tag

    def _get_image_id(self) -> str | None:
        try:
            result = subprocess.run(
                ["docker", "images", "-q", f"{self.image_name}:{self.tag}"],
                capture_output=True,
                text=True,
                check=True,
            )
            image_id = result.stdout.strip()
            return image_id if image_id else None
        except subprocess.CalledProcessError:
            return None

    def _build_image(self, context_path: str) -> bool:
        try:
            subprocess.run(
                [
                    "docker",
                    "buildx",
                    "build",
                    "-t",
                    f"{self.image_name}:{self.tag}",
                    context_path,
                ],
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
