"""m4a Splitter - GUI tool to split m4a audio files into equal parts."""
from __future__ import annotations

import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BOTH, IntVar, StringVar, Tk, filedialog, messagebox, ttk


APP_NAME = "m4a Splitter"
APP_VERSION = "1.0.0"

# subprocess flag to avoid flashing a console window on Windows.
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _candidate_bin_dirs() -> list[Path]:
    """Return directories that may contain ffmpeg/ffprobe, in priority order."""
    dirs: list[Path] = []

    # 1) PyInstaller --onefile bundle
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        dirs.append(Path(meipass) / "bin")

    # 2) Folder next to the executable / script
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
    else:
        exe_dir = Path(__file__).resolve().parent.parent
    dirs.append(exe_dir / "bin")
    dirs.append(exe_dir)

    return dirs


def _resolve_tool(name: str) -> str | None:
    """Locate ffmpeg/ffprobe by checking bundled locations then PATH."""
    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    for d in _candidate_bin_dirs():
        candidate = d / exe_name
        if candidate.is_file():
            return str(candidate)

    # 3) PATH
    from shutil import which

    found = which(name) or which(exe_name)
    return found


def _run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    """Run a subprocess hiding the console window on Windows."""
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )


def get_duration_seconds(ffprobe: str, input_path: Path) -> float:
    """Return the duration of the audio file in seconds."""
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    proc = _run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{proc.stderr.strip()}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("ffprobe returned no duration. The file may be invalid.")
    try:
        return float(out)
    except ValueError as exc:
        raise RuntimeError(f"Unexpected ffprobe output: {out!r}") from exc


def split_file(
    ffmpeg: str,
    input_path: Path,
    output_dir: Path,
    parts: int,
    duration: float,
) -> list[Path]:
    """Split input_path into ``parts`` roughly-equal segments using stream copy."""
    if parts < 2:
        raise ValueError("parts must be >= 2")
    if duration <= 0:
        raise ValueError("duration must be positive")

    output_dir.mkdir(parents=True, exist_ok=True)

    pad_width = max(2, len(str(parts)))
    segment = duration / parts
    stem = input_path.stem
    suffix = input_path.suffix or ".m4a"
    outputs: list[Path] = []

    for i in range(parts):
        start = segment * i
        out_path = output_dir / f"{stem}_part{str(i + 1).zfill(pad_width)}{suffix}"
        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(input_path),
        ]
        # All but the last segment get an explicit duration; the last reads to EOF
        # so we don't lose tail samples to rounding.
        if i < parts - 1:
            cmd += ["-t", f"{segment:.3f}"]
        cmd += ["-c", "copy", "-map", "0:a", str(out_path)]

        proc = _run(cmd)
        if proc.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed on part {i + 1}:\n{proc.stderr.strip()}"
            )
        outputs.append(out_path)

    return outputs


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        root.title(f"{APP_NAME} {APP_VERSION}")
        root.geometry("640x320")
        root.resizable(False, False)

        self.input_var = StringVar()
        self.output_var = StringVar()
        self.parts_var = IntVar(value=2)
        self.status_var = StringVar(value="準備完了")

        self._build_ui()
        self._busy = False

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        frame = ttk.Frame(self.root)
        frame.pack(fill=BOTH, expand=True, padx=8, pady=8)

        # Row 1: input file
        ttk.Label(frame, text="分割するファイル:").grid(
            row=0, column=0, sticky="w", **pad
        )
        ttk.Entry(frame, textvariable=self.input_var, width=60).grid(
            row=1, column=0, columnspan=2, sticky="we", padx=12
        )
        ttk.Button(frame, text="参照...", command=self._on_browse_input).grid(
            row=1, column=2, padx=(4, 12)
        )

        # Row 2: output dir
        ttk.Label(frame, text="出力フォルダ:").grid(
            row=2, column=0, sticky="w", **pad
        )
        ttk.Entry(frame, textvariable=self.output_var, width=60).grid(
            row=3, column=0, columnspan=2, sticky="we", padx=12
        )
        ttk.Button(frame, text="参照...", command=self._on_browse_output).grid(
            row=3, column=2, padx=(4, 12)
        )
        hint = ttk.Label(
            frame,
            text="※ 出力フォルダ未指定なら入力ファイルと同じ場所になります",
            foreground="#888888",
        )
        hint.grid(row=4, column=0, columnspan=3, sticky="w", padx=12)

        # Row 3: parts
        ttk.Label(frame, text="分割数:").grid(row=5, column=0, sticky="w", **pad)
        self.parts_spin = ttk.Spinbox(
            frame, from_=2, to=999, textvariable=self.parts_var, width=8
        )
        self.parts_spin.grid(row=5, column=1, sticky="w", padx=4)

        # Row 4: action
        self.run_btn = ttk.Button(
            frame, text="分割実行", command=self._on_run
        )
        self.run_btn.grid(row=6, column=0, columnspan=3, pady=(10, 4))

        # Row 5: progress
        self.progress = ttk.Progressbar(frame, mode="indeterminate", length=560)
        self.progress.grid(row=7, column=0, columnspan=3, sticky="we", padx=12)

        # Row 6: status
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=8, column=0, columnspan=3, sticky="w", padx=12, pady=(6, 0)
        )

        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

    # --- handlers -------------------------------------------------------

    def _on_browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title="m4a ファイルを選択",
            filetypes=[("m4a ファイル", "*.m4a"), ("すべてのファイル", "*.*")],
        )
        if not path:
            return
        self.input_var.set(path)
        if not self.output_var.get().strip():
            self.output_var.set(str(Path(path).parent))

    def _on_browse_output(self) -> None:
        path = filedialog.askdirectory(title="出力フォルダを選択")
        if path:
            self.output_var.set(path)

    def _on_run(self) -> None:
        if self._busy:
            return

        input_str = self.input_var.get().strip()
        if not input_str:
            messagebox.showwarning(APP_NAME, "分割するファイルを指定してください。")
            return
        input_path = Path(input_str)
        if not input_path.is_file():
            messagebox.showwarning(
                APP_NAME, f"ファイルが見つかりません:\n{input_path}"
            )
            return

        output_str = self.output_var.get().strip()
        output_dir = Path(output_str) if output_str else input_path.parent

        try:
            parts = int(self.parts_var.get())
        except (ValueError, Exception):
            messagebox.showwarning(APP_NAME, "分割数は整数を指定してください。")
            return
        if parts < 2 or parts > 999:
            messagebox.showwarning(APP_NAME, "分割数は 2〜999 の範囲で指定してください。")
            return

        ffmpeg = _resolve_tool("ffmpeg")
        ffprobe = _resolve_tool("ffprobe")
        if not ffmpeg or not ffprobe:
            messagebox.showerror(
                APP_NAME,
                "ffmpeg が見つかりません。インストーラーから再インストールしてください。",
            )
            return

        self._set_busy(True)
        self.status_var.set("解析中...")
        thread = threading.Thread(
            target=self._worker,
            args=(ffmpeg, ffprobe, input_path, output_dir, parts),
            daemon=True,
        )
        thread.start()

    def _worker(
        self,
        ffmpeg: str,
        ffprobe: str,
        input_path: Path,
        output_dir: Path,
        parts: int,
    ) -> None:
        try:
            duration = get_duration_seconds(ffprobe, input_path)
            self._post_status(
                f"分割中... ({parts} 分割 / {duration:.1f} 秒)"
            )
            outputs = split_file(ffmpeg, input_path, output_dir, parts, duration)
        except Exception as exc:  # surfaced to user
            self.root.after(0, self._on_done, False, str(exc), None)
            return
        self.root.after(0, self._on_done, True, None, outputs)

    def _post_status(self, msg: str) -> None:
        self.root.after(0, self.status_var.set, msg)

    def _on_done(
        self,
        ok: bool,
        err: str | None,
        outputs: list[Path] | None,
    ) -> None:
        self._set_busy(False)
        if ok:
            count = len(outputs) if outputs else 0
            self.status_var.set(f"完了: {count} ファイル出力しました")
            messagebox.showinfo(
                APP_NAME, f"分割が完了しました。\n出力ファイル数: {count}"
            )
        else:
            self.status_var.set("エラーが発生しました")
            messagebox.showerror(APP_NAME, err or "不明なエラー")

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        if busy:
            self.run_btn.state(["disabled"])
            self.progress.start(12)
        else:
            self.run_btn.state(["!disabled"])
            self.progress.stop()


def main() -> int:
    root = Tk()
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
