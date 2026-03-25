import hashlib
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UpdateInfo:
    latest_version: str
    zip_url: str
    sha256: str


def _parse_version_tuple(v: str) -> tuple[int, ...]:
    """
    Best-effort version parsing for tags like:
      v1.2.3, 1.2.3, release-1.2.3
    """
    v = (v or "").strip()
    v = v.lstrip("vV")
    v = re.sub(r"[^0-9.]", "", v)
    parts = [p for p in v.split(".") if p != ""]
    nums: list[int] = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            nums.append(0)
    return tuple(nums)


def is_version_newer(latest: str, current: str) -> bool:
    return _parse_version_tuple(latest) > _parse_version_tuple(current)


class UpdateManager:
    """
    Handles:
      - GitHub Releases "latest" lookup
      - manifest.json download
      - update ZIP download + sha256 verification
      - spawning ota_updater.exe to perform the file replacement
    """

    def __init__(
        self,
        *,
        github_repo: str,
        current_version: str,
        config_dir: Path,
        github_api_url_template: str = "https://api.github.com/repos/{repo}/releases/latest",
        manifest_asset_name: str = "manifest.json",
        timeout_s: int = 20,
    ):
        self.github_repo = (github_repo or "").strip()
        self.current_version = current_version
        self.config_dir = Path(config_dir)
        self.github_api_url_template = github_api_url_template
        self.manifest_asset_name = manifest_asset_name
        self.timeout_s = timeout_s

        self.log_file = self.config_dir / "ota.log"

    def _write_log(self, msg: str):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(msg.rstrip() + "\n")
        except Exception:
            # OTA should never break the app start.
            pass

    def _get_latest_release_json(self) -> dict | None:
        repo = self.github_repo
        if not repo:
            repo = self._load_repo_from_embedded_source()
        if not repo:
            return None

        api_url = self.github_api_url_template.format(repo=repo)
        headers = {"User-Agent": "NiziPOS-OTA"}

        try:
            r = requests.get(api_url, headers=headers, timeout=self.timeout_s)
            if r.status_code != 200:
                return None
            return r.json()
        except Exception as e:
            self._write_log(f"[check_latest_release_json] failed: {e}")
            return None

    def _load_repo_from_embedded_source(self) -> str | None:
        """
        Allows fully-automatic OTA without requiring the user to edit config.json.

        CI can generate/patch `ota_source.json` during the build.
        """
        try:
            installed_dir = os.path.dirname(sys.executable)
            src_path = os.path.join(installed_dir, "ota_source.json")
            if not os.path.exists(src_path):
                return None

            import json

            with open(src_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            repo = (payload.get("github_repo") or "").strip()
            return repo or None
        except Exception as e:
            self._write_log(f"[load_repo_from_embedded_source] failed: {e}")
            return None

    def _download_text(self, url: str) -> str | None:
        headers = {"User-Agent": "NiziPOS-OTA"}
        try:
            r = requests.get(url, headers=headers, timeout=self.timeout_s)
            if r.status_code != 200:
                return None
            return r.text
        except Exception as e:
            self._write_log(f"[download_text] failed: {e}")
            return None

    def _download_to_file(self, url: str, dest_path: Path):
        headers = {"User-Agent": "NiziPOS-OTA"}
        # Use a larger read timeout for big ZIP downloads.
        timeout = (10, max(60, int(self.timeout_s) * 6))
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)

    def _sha256_file(self, path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                h.update(block)
        return h.hexdigest()

    def _get_update_info(self) -> UpdateInfo | None:
        release = self._get_latest_release_json()
        if not release:
            return None

        assets = release.get("assets") or []
        manifest_asset = next(
            (a for a in assets if (a.get("name") or "") == self.manifest_asset_name),
            None,
        )
        if not manifest_asset:
            self._write_log("[get_update_info] manifest.json asset not found")
            return None

        manifest_url = manifest_asset.get("browser_download_url")
        if not manifest_url:
            return None

        manifest_text = self._download_text(manifest_url)
        if not manifest_text:
            return None

        try:
            manifest = requests.utils.json_loads(manifest_text)
        except Exception:
            # Fallback to std json parse:
            import json

            try:
                manifest = json.loads(manifest_text)
            except Exception as e:
                self._write_log(f"[get_update_info] manifest parse failed: {e}")
                return None

        latest_version = str(manifest.get("version") or release.get("tag_name") or "")
        sha256 = str(manifest.get("sha256") or "")
        if not latest_version or not sha256:
            self._write_log("[get_update_info] manifest missing version/sha256")
            return None

        zip_url = None

        # Preferred: manifest provides the exact zip URL.
        if manifest.get("zip_url"):
            zip_url = str(manifest["zip_url"])

        # Alternate: manifest provides the zip asset name.
        if not zip_url and manifest.get("zip_asset_name"):
            zip_asset_name = str(manifest["zip_asset_name"])
            zip_asset = next((a for a in assets if a.get("name") == zip_asset_name), None)
            if zip_asset and zip_asset.get("browser_download_url"):
                zip_url = str(zip_asset["browser_download_url"])

        if not zip_url:
            self._write_log("[get_update_info] zip_url not found in manifest/assets")
            return None

        if not is_version_newer(latest_version, self.current_version):
            return None

        return UpdateInfo(latest_version=latest_version, zip_url=zip_url, sha256=sha256)

    def prompt_and_update(self, parent_widget=None) -> bool:
        """
        Returns True if the updater was launched (caller should stop starting the app).
        Returns False if no update / user declined / download failed.
        """
        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
        except Exception as e:
            self._write_log(f"[prompt_and_update] PyQt6 import failed: {e}")
            return False

        info = self._get_update_info()
        if not info:
            return False

        # Prompt-first UX.
        msg = (
            f"An update is available.\n\n"
            f"Current: {self.current_version}\n"
            f"Latest:  {info.latest_version}\n\n"
            f"Download and update now?"
        )

        reply = QMessageBox.question(
            parent_widget,
            "NiziPOS Update",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return False

        progress = QProgressDialog("Downloading update…", None, 0, 0, parent_widget)
        progress.setWindowTitle("NiziPOS Update")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        try:
            tmp_dir = Path(tempfile.gettempdir()) / "nizipos_ota"
            zip_path = tmp_dir / f"update_{info.latest_version}.zip"
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass

            self._write_log(f"[download] url={info.zip_url}")
            QApplication.processEvents()
            self._download_to_file(info.zip_url, zip_path)

            self._write_log("[download] verifying sha256…")
            QApplication.processEvents()
            actual = self._sha256_file(zip_path)
            if actual.lower() != info.sha256.lower():
                QMessageBox.critical(
                    parent_widget,
                    "NiziPOS Update Failed",
                    "Update download verification failed (sha256 mismatch).",
                )
                return False

            # Spawn updater helper from the installed folder.
            installed_dir = Path(os.path.dirname(sys.executable))
            updater_exe = installed_dir / "ota_updater.exe"
            if not updater_exe.exists():
                QMessageBox.critical(
                    parent_widget,
                    "NiziPOS Update Failed",
                    f"Updater executable not found: {updater_exe}",
                )
                return False

            # Launch helper and let it perform the replacement.
            # Caller will stop starting the old app and exit immediately.
            main_exe = installed_dir / "NiziPOS.exe"
            log_path = str(self.log_file)
            subprocess.Popen(
                [
                    str(updater_exe),
                    "--target-dir",
                    str(installed_dir),
                    "--update-zip",
                    str(zip_path),
                    "--main-exe",
                    str(main_exe),
                    "--log-file",
                    log_path,
                ],
                close_fds=True,
                cwd=str(installed_dir),
            )
            return True
        except Exception as e:
            self._write_log(f"[prompt_and_update] failed: {e}")
            QMessageBox.critical(parent_widget, "NiziPOS Update Failed", str(e))
            return False
        finally:
            try:
                progress.close()
            except Exception:
                pass

