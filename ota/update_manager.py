import hashlib
import logging
import os
import re
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests


logger = logging.getLogger(__name__)

class OTALocalCancelled(Exception):
    """Raised when the user cancels an OTA download in the progress dialog."""


def _windows_prefers_light_theme() -> bool:
    """
    Best-effort Windows light/dark theme detection.
    Returns True if the user/app prefers light mode.
    """
    try:
        import winreg

        personalize = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, personalize) as key:
            apps_use_light, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            # 1 = light, 0 = dark
            return int(apps_use_light) == 1
    except Exception:
        return False


def _theme_colors(is_light: bool) -> dict[str, str]:
    # Red accent kept for both themes.
    accent = "#ef4444"
    accent2 = "#dc2626"

    if is_light:
        return {
            "dialog_bg": "#ffffff",
            "text": "#0f172a",
            "muted": "#475569",
            "border": "#e5e7eb",
            "secondary_bg": "#f1f5f9",
            "progress_bg": "#ffffff",
            "progress_bar_bg": "#f1f5f9",
            "chunk": accent,
            "cancel_bg": "#f8fafc",
            "cancel_border": "#e5e7eb",
        }

    return {
        "dialog_bg": "#111827",
        "text": "#e5e7eb",
        "muted": "#cbd5e1",
        "border": "#334155",
        "secondary_bg": "#0f172a",
        "progress_bg": "#0b1220",
        "progress_bar_bg": "#0f172a",
        "chunk": accent,
        "cancel_bg": "#0f172a",
        "cancel_border": "#334155",
    }


class UpdatePromptDialog:  # small namespace holder for type hints
    pass


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

        repo = self._normalize_github_repo(repo)
        if not repo:
            return None

        api_url = self.github_api_url_template.format(repo=repo)
        headers = {"User-Agent": "NiziPOS-OTA"}

        try:
            r = requests.get(api_url, headers=headers, timeout=self.timeout_s)
            if r.status_code != 200:
                self._write_log(f"[check_latest_release_json] status_code={r.status_code}")
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
            if not os.path.exists(src_path) or os.path.isdir(src_path):
                # PyInstaller may bundle `datas` under `_internal/`.
                src_path = os.path.join(installed_dir, "_internal", "ota_source.json")
                if os.path.exists(src_path) and os.path.isdir(src_path):
                    # Some pyinstaller layouts create a folder named `ota_source.json/`
                    src_path = os.path.join(src_path, "ota_source.json")
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

    def _normalize_github_repo(self, repo: str) -> str | None:
        """
        Accepts:
          - "owner/repo"
          - "https://github.com/owner/repo.git"
          - "git@github.com:owner/repo.git"
        and returns "owner/repo".
        """
        repo = (repo or "").strip()
        if not repo:
            return None

        # owner/repo
        if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            return repo

        # https://github.com/owner/repo(.git)
        m = re.search(r"github\.com/([^/]+)/([^/]+?)(?:\.git)?$", repo)
        if m:
            owner = m.group(1)
            name = m.group(2)
            if owner and name:
                return f"{owner}/{name}"

        # git@github.com:owner/repo(.git)
        m = re.search(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", repo)
        if m:
            owner = m.group(1)
            name = m.group(2)
            if owner and name:
                return f"{owner}/{name}"

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

    def _download_to_file(
        self,
        url: str,
        dest_path: Path,
        *,
        cancel_check=None,
        progress_dialog=None,
        label_prefix: str | None = None,
    ):
        headers = {"User-Agent": "NiziPOS-OTA"}
        # Use a larger read timeout for big ZIP downloads.
        timeout = (10, max(60, int(self.timeout_s) * 6))
        written = 0
        total = None
        with requests.get(url, headers=headers, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            try:
                cl = r.headers.get("Content-Length")
                if cl:
                    total = int(cl)
            except Exception:
                total = None

            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                if progress_dialog is not None and total:
                    progress_dialog.setRange(0, total)
                    progress_dialog.setValue(0)
                elif progress_dialog is not None:
                    # Indeterminate progress
                    progress_dialog.setRange(0, 0)

                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if not chunk:
                        continue
                    if cancel_check and cancel_check():
                        raise OTALocalCancelled()
                    f.write(chunk)
                    written += len(chunk)

                    if progress_dialog is not None and total:
                        progress_dialog.setValue(min(written, total))
                        if label_prefix:
                            percent = int((written * 100) / total)
                            progress_dialog.setLabelText(f"{label_prefix} {percent}%")

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
            manifest = json.loads(manifest_text)
        except Exception:
            self._write_log("[get_update_info] manifest parse failed")
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
            self._write_log(
                f"[get_update_info] latest_version={latest_version!r} current_version={self.current_version!r}"
            )
            return None

        return UpdateInfo(latest_version=latest_version, zip_url=zip_url, sha256=sha256)

    def prompt_and_update(self, parent_widget=None) -> bool:
        """
        Returns True if the updater was launched (caller should stop starting the app).
        Returns False if no update / user declined / download failed.
        """
        # Log resolved repo so we don't get confused by empty user input.
        raw_repo_input = self.github_repo
        resolved_repo = raw_repo_input or self._load_repo_from_embedded_source() or ""
        resolved_repo = self._normalize_github_repo(resolved_repo) or ""

        self._write_log(
            f"[startup_check] current_version={self.current_version!r} "
            f"github_repo={resolved_repo!r}"
        )

        try:
            from PyQt6.QtCore import Qt
            from PyQt6.QtWidgets import (
                QApplication,
                QDialog,
                QLabel,
                QPushButton,
                QHBoxLayout,
                QVBoxLayout,
                QMessageBox,
                QProgressDialog,
            )
        except Exception as e:
            self._write_log(f"[prompt_and_update] PyQt6 import failed: {e}")
            return False

        info = self._get_update_info()
        if not info:
            self._write_log("[startup_check] no update available")
            return False

        # Prompt-first UX: custom dialog for a consistent look on Windows.
        # This avoids QMessageBox stylesheet quirks that caused the "ugly / flat" buttons.
        current_version = self.current_version
        latest_version = info.latest_version
        is_light = _windows_prefers_light_theme()
        colors = _theme_colors(is_light)

        class UpdatePromptDialogImpl(QDialog):
            def __init__(self):
                super().__init__(parent_widget)
                self._accepted = False
                self.setWindowTitle("NiziPOS Update")
                self.setWindowModality(Qt.WindowModality.WindowModal)
                self.setMinimumWidth(460)
                self.setMinimumHeight(200)

                headline = QLabel("An update is available.")
                headline.setStyleSheet(f"color:{colors['text']}; font-size: 13.5pt; font-weight: 800;")

                informative = (
                    f"Current: {current_version}\n"
                    f"Latest:  {latest_version}\n\n"
                    "Download and update now?"
                )
                info_lbl = QLabel(informative)
                info_lbl.setWordWrap(True)
                info_lbl.setStyleSheet(f"color:{colors['muted']}; font-size: 11pt; font-weight: 600;")

                yes_btn = QPushButton("Yes")
                yes_btn.setObjectName("yesBtn")
                no_btn = QPushButton("No")
                no_btn.setObjectName("noBtn")

                def _accept_update():
                    self._accepted = True
                    self.accept()

                yes_btn.clicked.connect(_accept_update)
                no_btn.clicked.connect(self.reject)

                btn_row = QHBoxLayout()
                btn_row.setSpacing(16)
                btn_row.addStretch(1)
                btn_row.addWidget(yes_btn)
                btn_row.addWidget(no_btn)
                btn_row.addStretch(1)

                root = QVBoxLayout(self)
                root.setContentsMargins(18, 18, 18, 14)
                root.setSpacing(10)
                root.addWidget(headline)
                root.addWidget(info_lbl)
                root.addLayout(btn_row)

                # Build stylesheet without relying on Python's str.format (CSS uses braces).
                self.setStyleSheet(
                    (
                        "QDialog {"
                        f"background-color: {colors['dialog_bg']};"
                        f"color: {colors['text']};"
                        f"border: 1px solid {colors['border']};"
                        "border-radius: 10px;"
                        "}"
                        "QPushButton#yesBtn {"
                        f"background-color: {colors['chunk']};"
                        "color: #ffffff;"
                        "border: 0px;"
                        "border-radius: 10px;"
                        "padding: 9px 26px;"
                        "font-weight: 800;"
                        "min-width: 120px;"
                        "}"
                        "QPushButton#noBtn {"
                        f"background-color: {colors['secondary_bg']};"
                        "color: #ffffff;"
                        f"border: 1px solid {colors['border']};"
                        "border-radius: 10px;"
                        "padding: 9px 26px;"
                        "font-weight: 800;"
                        "min-width: 120px;"
                        "}"
                        "QPushButton:pressed {"
                        "transform: translateY(1px);"
                        "}"
                    )
                )

            def keyPressEvent(self, event):
                if event.key() == Qt.Key.Key_Escape:
                    self.reject()
                    event.accept()
                    return
                super().keyPressEvent(event)

            def closeEvent(self, event):
                # Treat window X as "No"/cancel.
                self._accepted = False
                self.reject()
                event.accept()

        dlg = UpdatePromptDialogImpl()
        dlg.exec()

        if not dlg._accepted:
            return False

        progress = QProgressDialog("Preparing update...", "Cancel", 0, 0, parent_widget)
        progress.setWindowTitle("NiziPOS Update")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setMinimumWidth(480)
        progress.setMinimumHeight(210)
        progress.setStyleSheet(
            f"""
QProgressDialog {{
  background-color: {colors['progress_bg']};
  color: {colors['text']};
  border: 1px solid {colors['border']};
  border-radius: 14px;
  padding: 22px;
}}
QLabel {{
  color: {colors['muted']};
  font-size: 14pt;
  font-weight: 800;
  margin-bottom: 10px;
}}
QPushButton {{
  border-radius: 12px;
  padding: 10px 26px;
  font-weight: 700;
  color: {colors['text']};
  border: 1px solid {colors['cancel_border']};
  background-color: {colors['cancel_bg']};
}}
QProgressBar {{
  height: 16px;
  border-radius: 8px;
  background-color: {colors['progress_bar_bg']};
  border: 1px solid {colors['border']};
  margin: 8px 0px 18px 0px;
  qproperty-alignment: AlignCenter;
  font-size: 12pt;
  qproperty-textVisible: false;
}}
QProgressBar::chunk {{
  border-radius: 6px;
  background-color: {colors['chunk']};
}}
"""
        )
        progress.show()

        cancelled = {"value": False}

        def _cancel_check() -> bool:
            return cancelled["value"] or progress.wasCanceled()

        def _on_cancel():
            cancelled["value"] = True
            progress.setLabelText("Cancelling...")

        try:
            progress.canceled.connect(_on_cancel)
        except Exception:
            pass

        # If user presses the window X / closes the dialog, treat it as cancellation.
        try:
            def _on_finished():
                cancelled["value"] = progress.wasCanceled()

            progress.finished.connect(_on_finished)
        except Exception:
            pass

        try:
            tmp_dir = Path(tempfile.gettempdir()) / "nizipos_ota"
            zip_path = tmp_dir / f"update_{info.latest_version}.zip"
            if zip_path.exists():
                try:
                    zip_path.unlink()
                except Exception:
                    pass

            progress.setLabelText("Downloading update...")
            progress.setRange(0, 0)
            self._write_log(f"[download] url={info.zip_url}")
            QApplication.processEvents()
            self._download_to_file(
                info.zip_url,
                zip_path,
                cancel_check=_cancel_check,
                progress_dialog=progress,
                label_prefix="Downloading update...",
            )

            if progress.wasCanceled():
                self._write_log("[download] cancelled by user")
                return False

            progress.setLabelText("Verifying download...")
            QApplication.processEvents()

            self._write_log("[download] verifying sha256...")
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
        except OTALocalCancelled:
            self._write_log("[download] cancelled by user (exception)")
            return False
        except Exception as e:
            self._write_log(f"[prompt_and_update] failed: {e}")
            QMessageBox.critical(parent_widget, "NiziPOS Update Failed", str(e))
            return False
        finally:
            try:
                progress.close()
            except Exception:
                pass

