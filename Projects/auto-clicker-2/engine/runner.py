from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from models.image_library import ImageLibrary
from models.step import Step, StepType
from models.workflow import Workflow

LOCATE_INTERVAL = 0.35
CLICK_IMAGE_TIMEOUT = 8.0
STEP_PAUSE = 0.2


class RunCancelled(Exception):
    pass


@dataclass(frozen=True)
class RunEvent:
    kind: str
    message: str
    step_id: str | None = None
    index: int | None = None


def validate_workflow(workflow: Workflow, library: ImageLibrary) -> list[str]:
    errors: list[str] = []
    if not workflow.steps:
        errors.append("Workflow chưa có bước nào.")
        return errors
    for index, step in enumerate(workflow.steps, start=1):
        if step.type not in (StepType.WAIT_IMAGE, StepType.CLICK_IMAGE):
            continue
        image_id = str(step.params.get("image_id") or "")
        if not image_id:
            errors.append(f"Bước {index} ({step.type.label}): chưa chọn ảnh.")
            continue
        asset = library.get(image_id)
        if asset is None:
            errors.append(f"Bước {index} ({step.type.label}): ảnh không còn trong thư viện.")
            continue
        path = asset.file_path(library.images_dir)
        if not path.exists():
            errors.append(f"Bước {index} ({step.type.label}): không tìm thấy file {asset.filename}.")
    return errors


class WorkflowRunner:
    def __init__(
        self,
        workflow: Workflow,
        library: ImageLibrary,
        should_stop: Callable[[], bool],
        emit: Callable[[RunEvent], None],
    ) -> None:
        self.workflow = workflow
        self.library = library
        self._should_stop = should_stop
        self._emit = emit

    def run(self) -> str:
        try:
            import pyautogui
        except ImportError:
            self._emit(RunEvent("failed", "Chưa cài pyautogui. Chạy: python -m pip install pyautogui"))
            return "failed"

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        self._emit(RunEvent("log", "Bắt đầu chạy. Đưa chuột lên góc trên-trái màn hình để dừng khẩn cấp."))

        try:
            for index, step in enumerate(self.workflow.steps):
                self._check_stop()
                label = f"Bước {index + 1}/{len(self.workflow.steps)}: {step.type.label}"
                self._emit(RunEvent("step_started", label, step.id, index))
                try:
                    self._execute(pyautogui, step)
                except (RunCancelled, pyautogui.FailSafeException):
                    raise
                except Exception as exc:
                    self._emit(RunEvent("failed", f"{label} — lỗi: {exc}", step.id, index))
                    return "failed"
                self._emit(RunEvent("step_success", f"{label} — xong", step.id, index))
                time.sleep(STEP_PAUSE)
        except RunCancelled:
            self._emit(RunEvent("cancelled", "Đã dừng workflow."))
            return "cancelled"
        except pyautogui.FailSafeException:
            self._emit(RunEvent("cancelled", "Đã dừng khẩn cấp (chuột ở góc màn hình)."))
            return "cancelled"

        self._emit(RunEvent("finished", "Hoàn thành workflow."))
        return "finished"

    def _execute(self, pyautogui, step: Step) -> None:
        if step.type is StepType.WAIT_IMAGE:
            timeout = float(step.params.get("timeout_seconds") or 10)
            box = self._wait_for_image(pyautogui, step, timeout)
            self._emit(RunEvent("log", f"Đã thấy ảnh tại {box}", step.id))
            return
        if step.type is StepType.CLICK_IMAGE:
            box = self._wait_for_image(pyautogui, step, CLICK_IMAGE_TIMEOUT)
            center = pyautogui.center(box)
            pyautogui.click(
                center.x,
                center.y,
                clicks=max(1, int(step.params.get("clicks") or 1)),
                button=str(step.params.get("button") or "left"),
            )
            self._emit(RunEvent("log", f"Click ảnh tại ({center.x}, {center.y})", step.id))
            return
        if step.type is StepType.CLICK_COORDINATE:
            x = int(step.params.get("x") or 0)
            y = int(step.params.get("y") or 0)
            pyautogui.click(
                x,
                y,
                clicks=max(1, int(step.params.get("clicks") or 1)),
                button=str(step.params.get("button") or "left"),
            )
            self._emit(RunEvent("log", f"Click tọa độ ({x}, {y})", step.id))
            return
        if step.type is StepType.TYPE_TEXT:
            text = str(step.params.get("text") or "")
            interval = float(step.params.get("interval") or 0.05)
            if not text:
                self._emit(RunEvent("log", "Bỏ qua gõ text (nội dung trống)", step.id))
                return
            self._type_text(pyautogui, text, interval)
            self._emit(RunEvent("log", "Đã gõ text", step.id))
            return
        if step.type is StepType.PRESS_KEY:
            keys = str(step.params.get("keys") or "enter")
            self._press_keys(pyautogui, keys)
            self._emit(RunEvent("log", f"Đã gõ phím {keys}", step.id))
            return
        raise ValueError(f"Không hỗ trợ loại bước: {step.type}")

    def _wait_for_image(self, pyautogui, step: Step, timeout: float):
        path = self._image_path(step)
        confidence = float(step.params.get("confidence") or 0.8)
        deadline = time.monotonic() + max(0.2, timeout)
        while True:
            self._check_stop()
            box = self._locate(pyautogui, path, confidence)
            if box is not None:
                return box
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Không thấy ảnh '{path.name}' sau {timeout}s.")
            time.sleep(LOCATE_INTERVAL)

    def _image_path(self, step: Step) -> Path:
        image_id = str(step.params.get("image_id") or "")
        path = self.library.file_path(image_id)
        if not path.exists():
            raise FileNotFoundError(f"Không tìm thấy file ảnh: {path}")
        return path

    def _locate(self, pyautogui, path: Path, confidence: float):
        image = str(path)
        confidence = min(max(confidence, 0.1), 0.99)
        try:
            return pyautogui.locateOnScreen(image, confidence=confidence)
        except Exception as exc:
            if _is_not_found(exc):
                return None
            if "confidence" not in str(exc).lower() and "opencv" not in str(exc).lower() and not isinstance(exc, TypeError):
                raise
        try:
            return pyautogui.locateOnScreen(image)
        except Exception as exc:
            if _is_not_found(exc):
                return None
            raise

    def _type_text(self, pyautogui, text: str, interval: float) -> None:
        self._check_stop()
        if text.isascii():
            pyautogui.write(text, interval=max(0.0, interval))
            return
        try:
            import pyperclip
        except ImportError:
            pyautogui.write(text, interval=max(0.0, interval))
            return
        previous = None
        try:
            previous = pyperclip.paste()
        except Exception:
            previous = None
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
        if previous is not None:
            try:
                pyperclip.copy(previous)
            except Exception:
                pass

    def _press_keys(self, pyautogui, spec: str) -> None:
        parts = [part.strip().lower() for part in spec.replace(" ", "").split("+") if part.strip()]
        if not parts:
            raise ValueError("Chưa nhập phím cần gõ.")
        self._check_stop()
        if len(parts) == 1:
            pyautogui.press(parts[0])
        else:
            pyautogui.hotkey(*parts)

    def _check_stop(self) -> None:
        if self._should_stop():
            raise RunCancelled()


def _is_not_found(exc: Exception) -> bool:
    name = type(exc).__name__
    return name in {"ImageNotFoundException", "ImageNotFound"} or "not found" in str(exc).lower()
