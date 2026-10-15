"""Application entry point."""

from pathlib import Path
import sys

from app.main_window import MainWindow


def main() -> None:
    # Ensure data/workflows directory exists
    workflows_dir = Path("data/workflows")
    workflows_dir.mkdir(parents=True, exist_ok=True)

    app = MainWindow(workflows_dir=workflows_dir)
    app.mainloop()


if __name__ == "__main__":
    main()
