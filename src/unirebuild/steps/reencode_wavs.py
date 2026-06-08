import glob
import logging
import os.path
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


# https://github.com/SamboyCoding/Fmod5Sharp/issues/9
class ReencodeWavs(PatcherStep):
    def __init__(self, glob_pattern: str = "Assets/**/*.wav"):
        self.glob_pattern = glob_pattern

    def get_dependencies(self) -> list[str]:
        return ["ffmpeg"]

    def execute(self, context: PatcherContext):
        ffmpeg_path = context.find_executable("ffmpeg")
        wav_files = glob.glob(
            os.path.join(context.workspace_dir, self.glob_pattern), recursive=True
        )
        logging.info("Re-encoding %d .wav files...", len(wav_files))

        for wav_file in wav_files:
            temp_wav_file = wav_file + ".temp.wav"
            context.run_cmd(
                [ffmpeg_path, "-y", "-i", wav_file, "-map_metadata", "0", temp_wav_file]
            )
            shutil.move(temp_wav_file, wav_file)
