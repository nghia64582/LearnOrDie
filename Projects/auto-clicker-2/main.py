from app.main_window import MainWindow
from app.paths import ensure_data_dirs


def main() -> None:
    ensure_data_dirs()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
