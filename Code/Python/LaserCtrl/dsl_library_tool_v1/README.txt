DSL Library Manager v1

Requirements:
- Python 3.10+
- Tkinter (normally included with standard Windows Python)

Run:
    python main.py

Each *.txt file is one DSL.

File format:
[NAME]
LM2596S-ZX001

[DESCRIPTION]
DC-DC converter

[DSL]
ADD 0 0 LM2596
R 0 0 30 20
END

Supported commands:
C R RC LH LV L A P M ADD ROTATE END FIRST

Notes:
- Preview approximates C/A with line segments for display.
- Existing G-code generation should continue using the original exact arc/tab implementation.
- The preview uses a Windows-friendly Segoe UI font and the DSL editor uses Consolas.
