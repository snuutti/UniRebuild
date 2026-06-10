import logging
import os
import shutil
import struct

from unirebuild.context import PatcherContext
from unirebuild.ios.cgbi import cgbi_to_png
from unirebuild.ios.plist import extract_plist_icon_filenames
from unirebuild.steps import PatcherStep


class ExtractAppIcon(PatcherStep):
    def __init__(self, output_path: str):
        self.output_path = output_path
        # todo: add option to create .meta file

    @staticmethod
    def get_png_dimensions(file_path: str) -> tuple[int, int]:
        with open(file_path, "rb") as f:
            header = f.read(24)
            if header[:8] == b"\x89PNG\r\n\x1a\n":
                width, height = struct.unpack(">II", header[16:24])
                return width, height

        raise ValueError("Not a valid PNG file")

    def extract_android_icon(self, context: PatcherContext, app_path: str):
        biggest_icon_path = None
        biggest_icon_size = 0

        for root, dirs, files in os.walk(os.path.join(app_path, "res")):
            for file in files:
                if file == "app_icon.png":
                    icon_path = os.path.join(root, file)
                    width, height = self.get_png_dimensions(icon_path)
                    icon_size = width * height

                    if biggest_icon_path is None or icon_size > biggest_icon_size:
                        biggest_icon_size = icon_size
                        biggest_icon_path = icon_path

        if biggest_icon_path is None:
            raise FileNotFoundError("No app_icon.png found")

        shutil.copy(
            biggest_icon_path, os.path.join(context.workspace_dir, self.output_path)
        )

        logging.info(
            "Extracted app icon '%s' to '%s'.", biggest_icon_path, self.output_path
        )

    def extract_ios_icon(self, context: PatcherContext, app_path: str):
        root_path = None
        plist_path = None
        for root, dirs, files in os.walk(app_path):
            if "Info.plist" in files:
                root_path = root
                plist_path = os.path.join(root_path, "Info.plist")
                break

        if not plist_path:
            raise FileNotFoundError("Info.plist not found in the app bundle")

        icon_filenames = extract_plist_icon_filenames(plist_path)

        temp_icon_dir = context.get_temp_path("icon")
        os.makedirs(temp_icon_dir, exist_ok=True)

        biggest_icon_path = None
        biggest_icon_size = 0

        for icon_filename in icon_filenames:
            icon_path = os.path.join(root_path, icon_filename)
            if not os.path.isfile(icon_path):
                continue

            png_data = cgbi_to_png(icon_path)
            if png_data is None:
                continue

            png_path = os.path.join(temp_icon_dir, icon_filename)
            with open(png_path, "wb") as f:
                f.write(png_data)

            width, height = self.get_png_dimensions(png_path)
            icon_size = width * height

            if biggest_icon_path is None or icon_size > biggest_icon_size:
                biggest_icon_size = icon_size
                biggest_icon_path = png_path

        if biggest_icon_path is None:
            raise FileNotFoundError("No valid icons found in the app bundle")

        shutil.copy(
            biggest_icon_path, os.path.join(context.workspace_dir, self.output_path)
        )

        logging.info(
            "Extracted app icon '%s' to '%s'.", biggest_icon_path, self.output_path
        )

    def execute(self, context: PatcherContext):
        app_path = os.path.join(context.get_extracted_path(), "app")

        if os.path.isfile(os.path.join(app_path, "AndroidManifest.xml")):
            self.extract_android_icon(context, app_path)
        elif os.path.isdir(os.path.join(app_path, "Payload")):
            self.extract_ios_icon(context, app_path)
        else:
            raise Exception("Unsupported app format")
