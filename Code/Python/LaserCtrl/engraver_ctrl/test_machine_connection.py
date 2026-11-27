#!/usr/bin/env python3
"""Tests for Engraver/Machine serial connect, disconnect, STOP recovery, jog, and Set Zero."""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_APP = os.path.dirname(_HERE)
if _APP not in sys.path:
    sys.path.insert(0, _APP)


def _state_of(widget):
    return str(widget.cget("state"))


def _is_disabled(widget):
    state = _state_of(widget)
    return state == "disabled" or "disabled" in state.split()


def _is_enabled(widget):
    return not _is_disabled(widget)


class FakeSerial:
    """Minimal serial.Serial stand-in. timeout=0 so readers do not busy-wait."""

    def __init__(self, responses=None, timeout=0, auto=True, reset_alarm=True):
        self.timeout = timeout
        self.is_open = True
        self.closed = False
        self.writes = []
        self._responses = list(responses or [])
        self.auto = auto
        self.reset_alarm = reset_alarm
        self.exc_on_write = None
        self.exc_on_read = None
        self.state = "Idle"
        self.mpos = [0.0, 0.0, 0.0]
        self.wco = [0.0, 0.0, 0.0]
        self._lock = threading.Lock()

    def write(self, data):
        if self.exc_on_write is not None:
            raise self.exc_on_write
        if not isinstance(data, (bytes, bytearray)):
            data = str(data).encode()
        data = bytes(data)
        with self._lock:
            self.writes.append(data)
            if self.auto:
                self._auto_reply(data)
        return len(data)

    def _auto_reply(self, data):
        if data == b"!":
            self.state = "Hold"
            return
        if data == b"\x18":
            self.state = "Alarm" if self.reset_alarm else "Idle"
            self._responses.append(b"Grbl 1.1h ['$' for help]\n")
            if self.reset_alarm:
                self._responses.append(b"[MSG:Reset to continue]\n")
            return
        if data == b"?":
            mpos = ",".join(f"{v:.3f}" for v in self.mpos)
            wco = ",".join(f"{v:.3f}" for v in self.wco)
            self._responses.append(
                f"<{self.state}|MPos:{mpos}|WCO:{wco}|FS:0,0>\n".encode()
            )
            return
        text = data.decode(errors="ignore").strip()
        if text == "$X":
            self.state = "Idle"
            self._responses.append(b"[MSG:Caution: Unlocked]\n")
            self._responses.append(b"ok\n")
            return
        if text.startswith("G10"):
            # G10 L20 Pn X.. Y.. : current position becomes the given work coords.
            self._apply_g10_l20(text)
            self._responses.append(b"ok\n")
            return
        if text.startswith("M5") or text.startswith("$J=") or text.startswith("G"):
            self._responses.append(b"ok\n")
            if text.startswith("$J="):
                self._apply_jog(text)
                self.state = "Idle"
            return

    def flush(self):
        pass

    def readline(self):
        if self.exc_on_read is not None:
            raise self.exc_on_read
        with self._lock:
            if self._responses:
                item = self._responses.pop(0)
                if isinstance(item, Exception):
                    raise item
                if isinstance(item, str):
                    item = item.encode()
                if not item.endswith(b"\n"):
                    item += b"\n"
                return item
            return b""

    def close(self):
        self.closed = True
        self.is_open = False

    def reset_input_buffer(self):
        # Keep queued auto-replies; tests inject them on write.
        return

    def reset_output_buffer(self):
        return

    def wrote_bytes(self, fragment):
        if isinstance(fragment, str):
            fragment = fragment.encode()
        return any(fragment in w for w in self.writes)

    def _apply_jog(self, text):
        import re
        for axis, value in re.findall(r"([XYZ])(-?\d+\.?\d*)", text):
            idx = "XYZ".index(axis)
            self.mpos[idx] += float(value)

    def _apply_g10_l20(self, text):
        import re
        # WCO = MPos - target WPos (missing axes stay 0).
        target = [0.0, 0.0, 0.0]
        for axis, value in re.findall(r"([XYZ])(-?\d+\.?\d*)", text):
            target["XYZ".index(axis)] = float(value)
        self.wco = [m - t for m, t in zip(self.mpos, target)]


class Host:
    def __init__(self):
        self.font = ("Segoe UI", 10)
        self.ser = None


class MachineConnectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import tkinter as tk
        from common.ui import enable_dpi_awareness, init_fonts

        enable_dpi_awareness()
        cls.root = tk.Tk()
        cls.root.withdraw()
        init_fonts(cls.root, size=10)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        from engraver_ctrl.tab_machine import MachineTab

        self.mb_patch = mock.patch("engraver_ctrl.tab_machine.messagebox")
        self.sleep_patch = mock.patch("engraver_ctrl.tab_machine.time.sleep", return_value=None)
        self.log_patch = mock.patch("engraver_ctrl.tab_machine.LOG_FILE", os.devnull)
        self.mb_patch.start()
        self.sleep_patch.start()
        self.log_patch.start()
        self.host = Host()
        self.tab = MachineTab(self.root, self.host)
        try:
            # Run after_idle(preview_gcode) now so it is not left for tearDown.
            self.root.update()
        except Exception:
            pass
        self.addCleanup(self._cleanup_tab)
        self.addCleanup(self.mb_patch.stop)
        self.addCleanup(self.sleep_patch.stop)
        self.addCleanup(self.log_patch.stop)

    def _cleanup_tab(self):
        try:
            self.root.update()
        except Exception:
            pass
        try:
            self.tab.destroy()
        except Exception:
            pass

    def _do_jog(self, axis, direction):
        """Run the jog worker on this thread (no mainloop, so after() would deadlock)."""
        self.assertTrue(self.host.ser)
        self.assertFalse(self.tab.is_running)
        if self.tab.stop_event.is_set():
            self.tab.stop_event.clear()
        step = float(self.tab.jog_step_var.get())
        cmd = self.tab.build_jog_command(axis, direction, step)
        self.assertTrue(self.tab.jog_lock.acquire(blocking=False))
        self.tab._jog_worker(cmd)

    def test_initial_status_is_disconnected(self):
        from engraver_ctrl.tab_machine import STATUS_DISCONNECTED_FG

        self.assertEqual(self.tab.connection_status.cget("text"), "Disconnected")
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_DISCONNECTED_FG)
        self.assertTrue(_is_enabled(self.tab.btn_connect))
        self.assertTrue(_is_disabled(self.tab.btn_disconnect))
        self.assertTrue(_is_disabled(self.tab.btn_unlock))
        self.assertTrue(_is_disabled(self.tab.btn_set_zero))

    def test_connect_success_updates_status_and_buttons(self):
        from engraver_ctrl.tab_machine import BAUD_RATE, STATUS_CONNECTED_FG

        fake = FakeSerial(reset_alarm=False)
        with mock.patch("engraver_ctrl.tab_machine.serial") as serial_mod:
            serial_mod.Serial.return_value = fake
            serial_mod.SerialException = OSError
            self.tab.combo_com.set("COM3")
            self.tab.connect_serial()

        self.assertIs(self.host.ser, fake)
        self.assertEqual(
            self.tab.connection_status.cget("text"),
            f"Connected (COM3 @ {BAUD_RATE})",
        )
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_CONNECTED_FG)
        self.assertTrue(_is_disabled(self.tab.btn_connect))
        self.assertTrue(_is_enabled(self.tab.btn_disconnect))
        self.assertTrue(_is_enabled(self.tab.btn_unlock))
        self.assertTrue(_is_enabled(self.tab.btn_set_zero))

    def test_connect_error_shows_red_status(self):
        from engraver_ctrl.tab_machine import STATUS_DISCONNECTED_FG

        with mock.patch("engraver_ctrl.tab_machine.serial") as serial_mod:
            serial_mod.Serial.side_effect = OSError("port busy")
            serial_mod.SerialException = OSError
            self.tab.combo_com.set("COM3")
            self.tab.connect_serial()

        self.assertIsNone(self.host.ser)
        text = self.tab.connection_status.cget("text")
        self.assertIn("Connect error", text)
        self.assertIn("port busy", text)
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_DISCONNECTED_FG)
        self.assertTrue(_is_enabled(self.tab.btn_connect))
        self.assertTrue(_is_disabled(self.tab.btn_disconnect))

    def test_connect_requires_a_port(self):
        self.tab.combo_com.set("  ")
        with mock.patch("engraver_ctrl.tab_machine.serial") as serial_mod:
            serial_mod.SerialException = OSError
            self.tab.connect_serial()
        self.assertIsNone(self.host.ser)
        self.assertEqual(self.tab.connection_status.cget("text"), "No COM port selected")
        self.assertTrue(_is_enabled(self.tab.btn_connect))

    def test_disconnect_closes_port_and_resets_ui(self):
        from engraver_ctrl.tab_machine import STATUS_DISCONNECTED_FG

        fake = FakeSerial(reset_alarm=False)
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)

        self.tab.disconnect_serial()

        self.assertTrue(fake.closed)
        self.assertIsNone(self.host.ser)
        self.assertEqual(self.tab.connection_status.cget("text"), "Disconnected")
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_DISCONNECTED_FG)
        self.assertTrue(_is_enabled(self.tab.btn_connect))
        self.assertTrue(_is_disabled(self.tab.btn_disconnect))
        self.assertTrue(_is_disabled(self.tab.btn_set_zero))

    def test_shutdown_connection_closes_fake_serial(self):
        fake = FakeSerial()
        self.host.ser = fake
        self.tab.shutdown_connection()
        self.assertTrue(fake.closed)
        self.assertIsNone(self.host.ser)

    def test_write_exception_marks_connection_lost(self):
        from engraver_ctrl.tab_machine import STATUS_DISCONNECTED_FG

        fake = FakeSerial(auto=False)
        fake.exc_on_write = OSError("device disconnected")
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)

        ok = self.tab._send_line_and_wait_ok("G0 X1\n", timeout=0.2)
        self.assertFalse(ok)
        self.assertIsNone(self.host.ser)
        self.assertTrue(fake.closed)
        text = self.tab.connection_status.cget("text")
        self.assertIn("Connection lost", text)
        self.assertIn("device disconnected", text)
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_DISCONNECTED_FG)
        self.assertTrue(_is_enabled(self.tab.btn_connect))
        self.assertTrue(_is_disabled(self.tab.btn_disconnect))

    def test_readline_exception_marks_connection_lost(self):
        fake = FakeSerial(auto=False)
        fake.exc_on_read = OSError("read failed")
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)

        ok = self.tab._send_line_and_wait_ok("G0 X1\n", timeout=0.2)
        self.assertFalse(ok)
        self.assertIsNone(self.host.ser)
        self.assertTrue(fake.closed)
        self.assertIn("Connection lost", self.tab.connection_status.cget("text"))

    def test_parse_grbl_state(self):
        from engraver_ctrl.tab_machine import MachineTab

        self.assertEqual(MachineTab._parse_grbl_state("<Idle|MPos:0,0,0|FS:0,0>"), "Idle")
        self.assertEqual(MachineTab._parse_grbl_state("<Alarm|WPos:1,2,3>"), "Alarm")
        self.assertEqual(MachineTab._parse_grbl_state("<Hold:0|MPos:0,0,0>"), "Hold")
        self.assertEqual(MachineTab._parse_grbl_state("<Hold:1|MPos:0,0,0>"), "Hold")
        self.assertIsNone(MachineTab._parse_grbl_state("ok"))

    def test_alarm_status_label_is_red(self):
        from engraver_ctrl.tab_machine import STATUS_DISCONNECTED_FG

        self.host.ser = FakeSerial()
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._apply_machine_state("Alarm")
        self.assertEqual(
            self.tab.connection_status.cget("text"),
            "Connected (COM3 @ 115200) — Alarm",
        )
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_DISCONNECTED_FG)

    def test_hold_status_label_is_orange(self):
        from engraver_ctrl.tab_machine import STATUS_HOLD_FG

        self.host.ser = FakeSerial()
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._apply_machine_state("Hold")
        self.assertEqual(
            self.tab.connection_status.cget("text"),
            "Connected (COM3 @ 115200) — Hold",
        )
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_HOLD_FG)

    def test_stop_then_jog_unlocks_and_uses_dollar_j(self):
        """Reproduce the user bug: STOP left Alarm + stop_event, so jog failed at G91."""
        from engraver_ctrl.tab_machine import BAUD_RATE, STATUS_CONNECTED_FG

        fake = FakeSerial(reset_alarm=True)
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = BAUD_RATE
        self.tab._set_connection_status(f"Connected (COM3 @ {BAUD_RATE})", connected=True)
        self.tab.is_running = True

        self.tab.stop_gcode()

        self.assertTrue(fake.wrote_bytes(b"!"), "STOP should feed-hold first")
        self.assertTrue(fake.wrote_bytes(b"\x18"), "STOP should soft-reset")
        self.assertTrue(fake.wrote_bytes(b"$X"), "STOP should auto-unlock after reset")
        self.assertTrue(fake.wrote_bytes(b"M5"), "STOP should turn the laser off after unlock")
        self.assertFalse(
            self.tab.stop_event.is_set(),
            "stop_event must be cleared so the next jog is not aborted",
        )
        self.assertEqual(fake.state, "Idle")
        status = self.tab.connection_status.cget("text")
        self.assertTrue(status.startswith("Connected (COM3 @ 115200)"))
        self.assertNotIn("Alarm", status)
        self.assertEqual(str(self.tab.connection_status.cget("fg")), STATUS_CONNECTED_FG)

        writes_after_stop = list(fake.writes)
        self._do_jog("Y", -1)

        jog_writes = fake.writes[len(writes_after_stop):]
        self.assertTrue(
            any(b"$J=" in w and b"Y-1.000" in w for w in jog_writes),
            f"$J= jog was not sent after STOP; writes={jog_writes!r}",
        )
        self.assertFalse(
            any(w.strip() == b"G91" for w in jog_writes),
            "legacy G91 jog should not be used",
        )
        # Jog must have succeeded (an ok was consumed) — state stays Idle.
        self.assertEqual(fake.state, "Idle")

    def test_jog_auto_unlocks_when_already_in_alarm(self):
        fake = FakeSerial(reset_alarm=True)
        fake.state = "Alarm"
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._apply_machine_state("Alarm")
        # Leftover stop flag from the old STOP path must not block jog.
        self.tab.stop_event.set()

        self._do_jog("X", 1)

        self.assertFalse(self.tab.stop_event.is_set())
        self.assertTrue(fake.wrote_bytes(b"?"))
        self.assertTrue(fake.wrote_bytes(b"$X"))
        self.assertTrue(any(b"$J=" in w and b"X1.000" in w for w in fake.writes))
        self.assertEqual(fake.state, "Idle")
        self.assertNotIn("Alarm", self.tab.connection_status.cget("text"))

    def test_build_jog_command_is_dollar_j(self):
        cmd = self.tab.build_jog_command("Y", -1, 1)
        self.assertTrue(cmd.startswith("$J=G91 Y-1.000 F"))
        self.assertTrue(cmd.endswith("\n"))

    def test_set_zero_command_is_g10_not_g92(self):
        from engraver_ctrl.tab_machine import SET_ZERO_CMD

        self.assertIn("G10 L20 P1 X0 Y0", SET_ZERO_CMD)
        self.assertNotIn("G92", SET_ZERO_CMD)
        self.assertTrue(SET_ZERO_CMD.endswith("\n"))

    def test_parse_grbl_wpos(self):
        from engraver_ctrl.tab_machine import MachineTab

        self.assertEqual(
            MachineTab._parse_grbl_wpos("<Idle|WPos:1.500,-2.000,0.000|FS:0,0>"),
            (1.5, -2.0, 0.0),
        )
        self.assertEqual(
            MachineTab._parse_grbl_wpos(
                "<Idle|MPos:10.000,5.000,0.000|WCO:10.000,5.000,0.000|FS:0,0>"
            ),
            (0.0, 0.0, 0.0),
        )
        self.assertEqual(
            MachineTab._parse_grbl_wpos(
                "<Idle|MPos:12.000,8.000,1.000|WCO:10.000,5.000,0.000|FS:0,0>"
            ),
            (2.0, 3.0, 1.0),
        )
        self.assertIsNone(MachineTab._parse_grbl_wpos("<Idle|MPos:1,2,3|FS:0,0>"))
        self.assertIsNone(MachineTab._parse_grbl_wpos("ok"))

    def test_set_zero_disabled_in_alarm_and_hold(self):
        fake = FakeSerial()
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._apply_machine_state("Alarm")
        self.assertTrue(_is_disabled(self.tab.btn_set_zero))
        self.tab._apply_machine_state("Hold")
        self.assertTrue(_is_disabled(self.tab.btn_set_zero))
        self.tab._apply_machine_state("Idle")
        self.assertTrue(_is_enabled(self.tab.btn_set_zero))

    def test_set_zero_disabled_while_running(self):
        fake = FakeSerial()
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)
        self.assertTrue(_is_enabled(self.tab.btn_set_zero))
        self.tab.is_running = True
        self.tab._sync_set_zero_button()
        self.assertTrue(_is_disabled(self.tab.btn_set_zero))

    def test_set_zero_requires_connection(self):
        self.tab.set_work_zero()
        from engraver_ctrl.tab_machine import messagebox
        messagebox.showerror.assert_called()
        self.assertIsNone(self.host.ser)

    def test_set_zero_ignored_when_not_idle(self):
        fake = FakeSerial()
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._apply_machine_state("Alarm")
        writes_before = list(fake.writes)
        self.tab.set_work_zero()
        self.assertEqual(fake.writes, writes_before)
        self.assertFalse(fake.wrote_bytes(b"G10"))

    def test_set_zero_sends_g10_and_logs_wpos(self):
        from engraver_ctrl.tab_machine import SET_ZERO_CMD

        fake = FakeSerial()
        fake.mpos = [12.0, 4.0, 0.0]
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)
        self.tab._machine_state = "Idle"

        logged = []
        self.tab.log = lambda msg: logged.append(msg)

        self.tab.set_work_zero()

        self.assertTrue(
            any(w.strip() == SET_ZERO_CMD.strip().encode() or SET_ZERO_CMD.encode() == w
                for w in fake.writes),
            f"G10 L20 was not sent; writes={fake.writes!r}",
        )
        self.assertTrue(fake.wrote_bytes(b"G10 L20 P1 X0 Y0"))
        self.assertFalse(fake.wrote_bytes(b"G92"))
        self.assertTrue(fake.wrote_bytes(b"?"))
        # Current machine position is now work (0, 0).
        self.assertEqual(fake.wco, [12.0, 4.0, 0.0])
        self.assertTrue(
            any("Set Zero" in m and "G10 L20 P1" in m for m in logged),
            f"missing Set Zero log: {logged!r}",
        )
        self.assertTrue(
            any(m.startswith("WPos:") and "0.000, 0.000" in m for m in logged),
            f"missing WPos log: {logged!r}",
        )
        self.assertTrue(_is_enabled(self.tab.btn_set_zero))

    def test_set_zero_after_jog_then_survives_stop_reset(self):
        """Jog then Set Zero; STOP soft-reset must not send G92.1 or G92."""
        fake = FakeSerial(reset_alarm=True)
        self.host.ser = fake
        self.tab._connected_port = "COM3"
        self.tab._connected_baud = 115200
        self.tab._set_connection_status("Connected (COM3 @ 115200)", connected=True)
        self.tab._machine_state = "Idle"

        self._do_jog("X", 1)
        self._do_jog("Y", 1)
        self.assertAlmostEqual(fake.mpos[0], 1.0)
        self.assertAlmostEqual(fake.mpos[1], 1.0)

        self.tab.set_work_zero()
        self.assertEqual(fake.wco[:2], [1.0, 1.0])

        self.tab.is_running = True
        self.tab.stop_gcode()

        # Soft reset happened, but work offset was not cleared (no G92/G92.1).
        self.assertTrue(fake.wrote_bytes(b"\x18"))
        self.assertFalse(any(b"G92" in w for w in fake.writes))
        self.assertEqual(fake.wco[:2], [1.0, 1.0])
        self.assertTrue(_is_enabled(self.tab.btn_set_zero))


if __name__ == "__main__":
    unittest.main()
