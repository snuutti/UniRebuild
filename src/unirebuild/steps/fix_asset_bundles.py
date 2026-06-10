import logging
import os.path

from unirebuild.context import PatcherContext
from unirebuild.steps import PatcherStep


class FixAssetBundles(PatcherStep):
    def execute(self, context: PatcherContext):
        logging.info("Fixing asset bundles...")

        asset_bundles_dir = os.path.join(
            context.workspace_dir, "Assets", "AssetBundles"
        )

        if not os.path.exists(asset_bundles_dir):
            raise FileNotFoundError(
                f"AssetBundles directory not found at {asset_bundles_dir}"
            )

        for root, dirs, files in os.walk(asset_bundles_dir):
            if root == asset_bundles_dir:
                continue

            relative_path = os.path.relpath(root, asset_bundles_dir)
            bundle_name = relative_path.split(os.sep)[0]

            for file in files:
                if not file.endswith(".meta"):
                    continue

                meta_path = os.path.join(root, file)

                with open(meta_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                content = "".join(lines)
                if "assetBundleName: " in content:
                    for i, line in enumerate(lines):
                        if line.startswith("  assetBundleName: "):
                            lines[i] = f"  assetBundleName: {bundle_name}\n"
                            break
                else:
                    lines.append(f"  assetBundleName: {bundle_name}\n")

                with open(meta_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
