# Steps to build
# run "pyinstaller --noconsole --icon=icon.ico --add-data "cards;cards" --add-data "card_deck;card_deck" main.py"
# copy "dist/main/main.exe" to "app/main.exe"
# copy "dist/main/_internal/cards" to "app/cards"
# copy "dist/main/_internal/card_deck" to "app/card_deck"
# auto press Y to confirm the build process
import os
import subprocess

def build_executable():
    command = [
        "pyinstaller",
        "--noconsole",
        "--icon=icon.ico",
        "--add-data",
        "cards;cards",
        "--add-data",
        "card_deck;card_deck",
        "main.py"
    ]
    subprocess.run(command)
    print("Executable built successfully.")
    # Move the built executable and data to the app directory
    if not os.path.exists("app"):
        os.makedirs("app")
    os.replace("dist/main/main.exe", "app/main.exe")
    os.replace("dist/main/_internal/cards", "app/cards")
    os.replace("dist/main/_internal/card_deck", "app/card_deck")

if __name__ == "__main__":
    build_executable()
    print("Build process completed.")