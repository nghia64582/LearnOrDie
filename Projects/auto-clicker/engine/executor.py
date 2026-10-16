"""Workflow execution engine for automating desktop graphs."""

from __future__ import annotations

import threading
import time
from typing import Callable, Optional

from PIL import Image

from engine.screen_matcher import (
    click_at,
    match_template,
    press_key,
    take_screenshot,
    type_text,
)
from models.node import Node
from models.node_definitions import (
    NODE_TYPE_CHECK_IMAGE,
    NODE_TYPE_CLICK_IMAGE,
    NODE_TYPE_END,
    NODE_TYPE_PRESS_KEY,
    NODE_TYPE_START,
    NODE_TYPE_TYPE_TEXT,
    NODE_TYPE_WAIT_IMAGE,
    NODE_TYPE_WAIT_TIME,
)
from models.workflow import Workflow
from storage.image_repository import ImageRepository


class WorkflowExecutor:
    """Runs a workflow graph step-by-step in a background worker thread."""

    def __init__(
        self,
        workflow: Workflow,
        image_repo: ImageRepository,
        on_log: Optional[Callable[[str], None]] = None,
        on_node_start: Optional[Callable[[str], None]] = None,
        on_node_done: Optional[Callable[[str, str], None]] = None,
        on_finish: Optional[Callable[[bool, str], None]] = None,
    ) -> None:
        self.workflow = workflow
        self.image_repo = image_repo
        self.on_log = on_log
        self.on_node_start = on_node_start
        self.on_node_done = on_node_done
        self.on_finish = on_finish

        self._stop_requested = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start workflow execution asynchronously in a background thread."""
        if self.is_running:
            return
        self._stop_requested = False
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Signal the running workflow to abort."""
        self._stop_requested = True
        self._log("⏹ Abort signal sent. Stopping workflow...")

    def _log(self, msg: str) -> None:
        if self.on_log:
            self.on_log(msg)

    def _run_loop(self) -> None:
        # Find START node
        start_nodes = [n for n in self.workflow.nodes if n.type == NODE_TYPE_START]
        if not start_nodes:
            self._log("❌ Error: No START node found in workflow.")
            if self.on_finish:
                self.on_finish(False, "No START node found")
            return

        current_node: Optional[Node] = start_nodes[0]
        step_count = 0
        max_steps = 1000  # Guard against infinite loops

        self._log(f"🚀 Starting workflow '{self.workflow.workflow.name}'...")

        try:
            while current_node and not self._stop_requested:
                step_count += 1
                if step_count > max_steps:
                    self._log("⚠️ Maximum execution step limit (1000) reached. Stopping.")
                    break

                node_id = current_node.id
                node_type = current_node.type
                node_name = current_node.name

                if self.on_node_start:
                    self.on_node_start(node_id)

                self._log(f"[{step_count}] Executing '{node_name}' ({node_type})...")

                branch_taken = "next"

                # Execute node behavior
                if node_type == NODE_TYPE_START:
                    branch_taken = "next"

                elif node_type == NODE_TYPE_END:
                    self._log(f"🏁 Reached END node '{node_name}'. Workflow completed successfully!")
                    if self.on_node_done:
                        self.on_node_done(node_id, "")
                    if self.on_finish:
                        self.on_finish(True, "Workflow completed successfully")
                    return

                elif node_type == NODE_TYPE_WAIT_TIME:
                    duration_ms = current_node.params.get("duration_ms", 1000)
                    self._log(f"⏳ Waiting {duration_ms} ms...")
                    # Sleep in small increments to respond quickly to stop requests
                    elapsed = 0
                    while elapsed < duration_ms and not self._stop_requested:
                        chunk = min(50, duration_ms - elapsed)
                        time.sleep(chunk / 1000.0)
                        elapsed += chunk
                    branch_taken = "success"

                elif node_type == NODE_TYPE_TYPE_TEXT:
                    text = str(current_node.params.get("text", ""))
                    self._log(f"⌨️ Typing text: {text!r}")
                    type_text(text)
                    branch_taken = "success"

                elif node_type == NODE_TYPE_PRESS_KEY:
                    key = str(current_node.params.get("key", "Enter"))
                    self._log(f"⌨️ Pressing key: '{key}'")
                    press_key(key)
                    branch_taken = "success"

                elif node_type == NODE_TYPE_CHECK_IMAGE:
                    image_id = str(current_node.params.get("image_id", ""))
                    threshold = float(current_node.params.get("threshold", 0.85))
                    found = self._check_image_present(image_id, threshold)
                    branch_taken = "true" if found else "false"
                    self._log(f"🔍 Check Image '{image_id}': {'Found (true)' if found else 'Not Found (false)'}")

                elif node_type == NODE_TYPE_WAIT_IMAGE:
                    image_id = str(current_node.params.get("image_id", ""))
                    condition = str(current_node.params.get("condition", "appear"))
                    timeout_ms = int(current_node.params.get("timeout_ms", 10000))
                    poll_ms = int(current_node.params.get("poll_interval_ms", 300))
                    self._log(f"⏳ Waiting for image '{image_id}' to {condition} (timeout: {timeout_ms} ms)...")

                    success = self._wait_for_image(image_id, condition, timeout_ms, poll_ms)
                    branch_taken = "success" if success else "timeout"
                    self._log(f"Result: {branch_taken}")

                elif node_type == NODE_TYPE_CLICK_IMAGE:
                    image_id = str(current_node.params.get("image_id", ""))
                    off_x = float(current_node.params.get("offset_x", 0.0))
                    off_y = float(current_node.params.get("offset_y", 0.0))
                    self._log(f"🖱️ Locating and clicking image '{image_id}'...")

                    clicked = self._click_image(image_id, off_x, off_y)
                    branch_taken = "success" if clicked else "failure"
                    self._log(f"Result: {branch_taken}")

                if self.on_node_done:
                    self.on_node_done(node_id, branch_taken)

                if self._stop_requested:
                    break

                # Advance to next node via matching outgoing edge
                matching_edges = [
                    e
                    for e in self.workflow.edges
                    if e.source == node_id and e.source_port == branch_taken
                ]

                if not matching_edges:
                    self._log(f"ℹ️ No outgoing connection from branch '{branch_taken}'. Workflow ending.")
                    if self.on_finish:
                        self.on_finish(True, "Ended: No further outgoing branch")
                    return

                target_id = matching_edges[0].target
                current_node = self.workflow.get_node(target_id)
                if not current_node:
                    self._log(f"❌ Error: Target node ID '{target_id}' does not exist.")
                    if self.on_finish:
                        self.on_finish(False, f"Target node '{target_id}' not found")
                    return

                time.sleep(0.05)

        except Exception as err:
            self._log(f"💥 Exception during execution: {err}")
            if self.on_finish:
                self.on_finish(False, str(err))
            return

        if self._stop_requested:
            self._log("🛑 Workflow was stopped by user.")
            if self.on_finish:
                self.on_finish(False, "Stopped by user")

    def _get_template_image(self, image_id: str) -> Optional[Image.Image]:
        item = self.image_repo.get_image(image_id)
        if not item or not item.file_path.is_file():
            # Check by filename as fallback
            for it in self.image_repo.list_images():
                if it.name == image_id or it.filename == image_id:
                    return Image.open(it.file_path)
            return None
        return Image.open(item.file_path)

    def _check_image_present(self, image_id: str, threshold: float) -> bool:
        tmpl = self._get_template_image(image_id)
        if tmpl is None:
            self._log(f"⚠️ Warning: Image ID '{image_id}' not found in image repository.")
            return False

        screen = take_screenshot()
        if screen is None:
            self._log("⚠️ Warning: Could not capture screen.")
            return False

        match = match_template(screen, tmpl, threshold=threshold)
        return match is not None

    def _wait_for_image(
        self, image_id: str, condition: str, timeout_ms: int, poll_ms: int
    ) -> bool:
        tmpl = self._get_template_image(image_id)
        if tmpl is None:
            self._log(f"⚠️ Warning: Image ID '{image_id}' not found.")
            return False

        start_time = time.time()
        timeout_sec = timeout_ms / 1000.0

        while (time.time() - start_time) < timeout_sec and not self._stop_requested:
            screen = take_screenshot()
            if screen:
                match = match_template(screen, tmpl, threshold=0.85)
                is_present = match is not None

                if condition == "appear" and is_present:
                    return True
                elif condition == "disappear" and not is_present:
                    return True

            time.sleep(max(0.05, poll_ms / 1000.0))

        return False

    def _click_image(self, image_id: str, off_x: float, off_y: float) -> bool:
        tmpl = self._get_template_image(image_id)
        if tmpl is None:
            self._log(f"⚠️ Warning: Image ID '{image_id}' not found.")
            return False

        screen = take_screenshot()
        if screen is None:
            self._log("⚠️ Warning: Could not capture screen.")
            return False

        match = match_template(screen, tmpl, threshold=0.85)
        if match:
            mx, my, mw, mh = match
            target_x = int(mx + mw / 2.0 + off_x)
            target_y = int(my + mh / 2.0 + off_y)
            self._log(f"🎯 Target matched at ({mx}, {my}). Clicking at ({target_x}, {target_y})...")
            click_at(target_x, target_y)
            return True

        return False
