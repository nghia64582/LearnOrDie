from app.main_window import MainWindow
from app.paths import ensure_data_dirs
from engine.screen import enable_dpi_awareness


def main() -> None:
    # Bật DPI awareness trước khi tạo cửa sổ để tọa độ đúng trên mọi màn hình
    enable_dpi_awareness()
    ensure_data_dirs()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
