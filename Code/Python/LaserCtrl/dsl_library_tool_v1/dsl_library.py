from pathlib import Path
import re


class DSLLibrary:
    def __init__(self, path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)

    def list_files(self):
        return sorted(self.path.glob("*.txt"), key=lambda p: p.name.lower())

    def load(self, path):
        text = Path(path).read_text(encoding="utf-8")
        sections = {"name": "", "description": "", "dsl": ""}
        current = None
        dsl_lines = []

        for line in text.splitlines():
            tag = line.strip()
            if tag == "[NAME]":
                current = "name"
            elif tag == "[DESCRIPTION]":
                current = "description"
            elif tag == "[DSL]":
                current = "dsl"
            elif current == "dsl":
                dsl_lines.append(line)
            elif current:
                if sections[current]:
                    sections[current] += "\n" + line
                else:
                    sections[current] = line

        sections["dsl"] = "\n".join(dsl_lines)
        return sections

    def save(self, path, name, description, dsl):
        content = (
            "[NAME]\n" + name + "\n\n"
            "[DESCRIPTION]\n" + description + "\n\n"
            "[DSL]\n" + dsl.rstrip() + "\n"
        )
        Path(path).write_text(content, encoding="utf-8")

    def delete(self, path):
        Path(path).unlink(missing_ok=True)

    def safe_filename(self, name):
        s = re.sub(r'[<>:"/\\\\|?*]+', "_", name).strip(" .")
        if not s:
            s = "new_dsl"
        base = self.path / f"{s}.txt"
        if not base.exists():
            return base.name
        i = 2
        while (self.path / f"{s}_{i}.txt").exists():
            i += 1
        return f"{s}_{i}.txt"
