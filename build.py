#!/usr/bin/env python3

import argparse
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path


class BuildManager:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.dist_dir = self.root_dir / "dist"
        self.releases_dir = self.root_dir / "dist" / "releases"
        self.build_dir = self.root_dir / "build"

    def clean_dirs(self):
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        if self.dist_dir.exists():
            for item in self.dist_dir.iterdir():
                if item.name != "releases":
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()

    def create_dirs(self):
        self.releases_dir.mkdir(parents=True, exist_ok=True)

    def get_platform_config(self, target_platform):
        configs = {
            "windows": {
                "name": "hiddenote.exe",
                "add_data": "assets;assets",
                "src_data": "src;src",
                "icon": "--icon=assets/icon.ico",
                "windowed": "--windowed",
            },
            "linux": {
                "name": "hiddenote",
                "add_data": "assets:assets",
                "src_data": "src:src",
                "icon": "",
                "windowed": "--windowed",
            },
            "macos": {
                "name": "hiddenote",
                "add_data": "assets:assets",
                "src_data": "src:src",
                "icon": "",
                "windowed": "--windowed",
            },
        }
        return configs.get(target_platform, configs["linux"])

    def build_platform(self, target_platform):
        print(f"Building for {target_platform}...")

        config = self.get_platform_config(target_platform)

        cmd = [
            "pyinstaller",
            "--onefile",
            config["windowed"],
            f"--add-data={config['add_data']}",
            f"--add-data={config['src_data']}",
            "main.py",
            f"--name={config['name'].replace('.exe', '')}",
        ]

        if config["icon"]:
            cmd.append(config["icon"])

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"{target_platform} build successful")
            return True
        except subprocess.CalledProcessError as e:
            print(f"{target_platform} build failed: {e.stderr}")
            return False

    def package_release(self, target_platform, tag):
        config = self.get_platform_config(target_platform)
        executable_name = config["name"]

        dist_exe = self.dist_dir / executable_name

        if not dist_exe.exists():
            current_platform = platform.system().lower()
            if current_platform == "windows":
                alt_exe = self.dist_dir / "hiddenote.exe"
                if alt_exe.exists():
                    dist_exe = alt_exe
                else:
                    print(f"Executable not found: {dist_exe}")
                    return False
            else:
                print(f"Executable not found: {dist_exe}")
                return False

        zip_name = f"hiddenote-{target_platform}-{tag}.zip"
        zip_path = self.releases_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(dist_exe, executable_name)

            readme_path = self.root_dir / "README.md"
            if readme_path.exists():
                zipf.write(readme_path, "README.md")

            license_path = self.root_dir / "LICENSE"
            if license_path.exists():
                zipf.write(license_path, "LICENSE")

        print(f"Package created: {zip_path}")
        return True

    def build_and_package(self, platforms, tag):
        self.create_dirs()

        success_count = 0

        for platform_name in platforms:
            print(f"\n{'=' * 50}")
            print(f"Processing {platform_name}")
            print(f"{'=' * 50}")

            self.clean_dirs()

            if self.build_platform(platform_name):
                if self.package_release(platform_name, tag):
                    success_count += 1
                else:
                    print(f"Failed to package {platform_name}")
            else:
                print(f"Failed to build {platform_name}")

        print(f"\n{'=' * 50}")
        print("Build Summary")
        print(f"{'=' * 50}")
        print(
            f"Successfully built and packaged: {success_count}/{len(platforms)} platforms"
        )

        if success_count > 0:
            print(f"\nReleases available in: {self.releases_dir}")
            for zip_file in self.releases_dir.glob("*.zip"):
                print(f"  - {zip_file.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Build hiddenote for multiple platforms"
    )
    parser.add_argument(
        "--platform",
        choices=["windows", "linux", "macos", "all"],
        default="all",
        help="Target platform(s) to build for",
    )
    parser.add_argument("--tag", required=True, help="Release tag (e.g., v1-0-0)")

    args = parser.parse_args()

    if args.platform == "all":
        platforms = ["windows", "linux", "macos"]
    else:
        platforms = [args.platform]

    current_platform = platform.system().lower()
    if current_platform == "darwin":
        current_platform = "macos"

    print(f"Current platform: {current_platform}")
    print(f"Target platforms: {', '.join(platforms)}")
    print(f"Release tag: {args.tag}")

    if len(platforms) > 1 and current_platform not in ["linux", "macos"]:
        print("Warning: Cross-platform building works best on Linux/macOS")

    builder = BuildManager()
    builder.build_and_package(platforms, args.tag)


if __name__ == "__main__":
    main()
