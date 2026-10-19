DSL Library Manager v1

Requirements:
- Python 3.10+
- Tkinter (normally included with standard Windows Python)

Run:
    python main.py

Storage:
DSL drawings are stored on the Cloudflare Worker KV REST API
(KV_BASE_URL in dsl_library.py), not in local files:
    dsl_library:v1:index        JSON list of drawings (name, key, sha256...)
    dsl_library:v1:file:<id>    JSON {"name", "description", "content", ...}
"content" is the text format below, byte-identical to the old *.txt files.
Index + downloaded drawings are cached in dsl_library/.dsl_kv_cache.json
so the list still opens offline (read-only; saving needs the server).

The *.txt files in dsl_library/ are the original files, already uploaded.
To upload txt files again (one-time migration, verifies byte-for-byte):
    python migrate_txt_to_kv.py [folder] [--overwrite]

Text format of one DSL:
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
