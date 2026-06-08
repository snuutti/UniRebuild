import glob
import logging
import os.path
import re
import shutil

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


# https://github.com/SamboyCoding/Fmod5Sharp/issues/12
class DecodeFsbAudio(PatcherStep):
    def __init__(self, glob_pattern: str = "Assets/**/*.audioclip.resS"):
        self.glob_pattern = glob_pattern

    def get_dependencies(self) -> list[str]:
        return ["vgmstream-cli"]

    def execute(self, context: PatcherContext):
        vgmstream_path = context.find_executable("vgmstream-cli")
        fsb_files = glob.glob(
            os.path.join(context.workspace_dir, self.glob_pattern), recursive=True
        )
        logging.info("Decoding %d FSB audio files...", len(fsb_files))

        for fsb_file in fsb_files:
            # We need to add the .fsb extension for vgmstream to recognize the file format
            temp_fsb_file = fsb_file + ".fsb"
            shutil.move(fsb_file, temp_fsb_file)

            output_wav_file = fsb_file.replace(".audioclip.resS", ".wav")
            context.run_cmd([vgmstream_path, temp_fsb_file, "-o", output_wav_file])

            os.remove(temp_fsb_file)

            audio_name = os.path.splitext(os.path.basename(output_wav_file))[0]
            audioclip_path = os.path.join(
                os.path.dirname(output_wav_file), audio_name + ".audioclip"
            )
            os.remove(audioclip_path)

            old_audio_meta_path = audioclip_path + ".meta"
            new_audio_meta_path = output_wav_file + ".meta"
            shutil.move(old_audio_meta_path, new_audio_meta_path)

            with open(new_audio_meta_path, "r", encoding="utf-8") as f:
                meta_content = f.read()

            audio_guid = re.search(r"guid: ([a-f0-9]{32})", meta_content).group(1)
            audio_asset_bundle_name = re.search(
                r"assetBundleName: (.+)", meta_content
            ).group(1)

            meta_content = (
                f"fileFormatVersion: 2\n"
                f"guid: {audio_guid}\n"
                f"AudioImporter:\n"
                f"  externalObjects: {{}}\n"
                f"  serializedVersion: 7\n"
                f"  defaultSettings:\n"
                f"    serializedVersion: 2\n"
                f"    loadType: 2\n"
                f"    sampleRateSetting: 0\n"
                f"    sampleRateOverride: 0\n"
                f"    compressionFormat: 1\n"
                f"    quality: 0\n"
                f"    conversionMode: 0\n"
                f"    preloadAudioData: 1\n"
                f"  platformSettingOverrides: {{}}\n"
                f"  forceToMono: 0\n"
                f"  normalize: 0\n"
                f"  loadInBackground: 1\n"
                f"  ambisonic: 0\n"
                f"  3D: 0\n"
                f"  userData: \n"
                f"  assetBundleName: {audio_asset_bundle_name}\n"
                f"  assetBundleVariant: \n"
            )

            with open(new_audio_meta_path, "w", encoding="utf-8") as f:
                f.write(meta_content)
