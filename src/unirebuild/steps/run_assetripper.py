import logging
import os
import shutil
import subprocess
import time
import urllib.parse
import urllib.request
import urllib.error

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class RunAssetRipper(PatcherStep):
    def get_dependencies(self) -> list[str]:
        return ["AssetRipper.GUI.Free"]

    def execute(self, context: PatcherContext):
        assetripper_path = context.find_executable("AssetRipper.GUI.Free")
        input_dir = context.get_extracted_path()
        output_dir = context.get_temp_path("RippedProject")

        cmd = [assetripper_path, "--headless", "--log=false", "--port=6464"]

        env = os.environ.copy()
        env["SOURCE_DATE_EPOCH"] = "1767225600"

        logging.info("Starting AssetRipper in the background...")
        process = subprocess.Popen(cmd, env=env)

        logging.info("Waiting for AssetRipper to start...")

        server_up = False
        for _ in range(10):
            if process.poll() is not None:
                raise RuntimeError("AssetRipper process terminated unexpectedly.")

            try:
                urllib.request.urlopen("http://127.0.0.1:6464/", timeout=2)
                server_up = True
                break
            except urllib.error.URLError:
                pass

            time.sleep(1)

        if not server_up:
            process.terminate()
            raise TimeoutError("Timed out waiting for AssetRipper to start.")

        logging.info("AssetRipper is running. Proceeding with load and export...")
        logging.info("This may take several minutes. Please wait...")

        try:
            load_data = urllib.parse.urlencode(
                {"path": os.path.abspath(input_dir)}
            ).encode("utf-8")
            load_req = urllib.request.Request(
                "http://127.0.0.1:6464/LoadFolder", data=load_data, method="POST"
            )
            load_req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urllib.request.urlopen(load_req, timeout=1800) as response:
                if response.status == 200:
                    logging.info("Load completed successfully!")
                else:
                    raise RuntimeError(
                        f"AssetRipper load failed with status code {response.status}"
                    )

            logging.info("Starting export... This may take several minutes.")

            export_data = urllib.parse.urlencode(
                {"path": os.path.abspath(output_dir)}
            ).encode("utf-8")
            export_req = urllib.request.Request(
                "http://127.0.0.1:6464/Export/UnityProject",
                data=export_data,
                method="POST",
            )
            export_req.add_header("Content-Type", "application/x-www-form-urlencoded")

            with urllib.request.urlopen(export_req, timeout=1800) as response:
                if response.status == 200:
                    logging.info("Export completed successfully!")
                else:
                    raise RuntimeError(
                        f"AssetRipper export failed with status code {response.status}"
                    )
        except urllib.error.URLError as e:
            raise RuntimeError(f"AssetRipper export request failed: {e}")
        finally:
            logging.info("Stopping AssetRipper...")
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
            logging.info("AssetRipper stopped.")

        exported_src = os.path.join(output_dir, "ExportedProject")
        if not os.path.exists(exported_src):
            raise FileNotFoundError(
                f"Expected exported project directory '{exported_src}' not found."
            )

        shutil.move(exported_src, context.workspace_dir)
