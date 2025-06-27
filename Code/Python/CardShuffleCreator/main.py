import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os
import random
import paramiko

# Constants
CARD_IDS = [0] + list(range(6, 30))  # 0 and 6->29
CARD_COUNT_PER_ID = 4
PLAYER_COUNT = 4
CARDS_PER_PLAYER = 19
TOTAL_CARDS = 100
CARDS_FOLDER = "cards"  # Adjust as needed
CARD_WIDTH = 30
CARD_HEIGHT = 115

class CardDeckTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Card Deck Setup Tool")
        self.root.geometry("1350x700")

        self.deck = []
        self.players = [[] for _ in range(PLAYER_COUNT)]
        self.rest = []
        self.images = {}
        self.selected_card = tk.IntVar(value=CARD_IDS[0])
        self.deck_name_var = tk.StringVar()
        self.selected_card_display = None

        # SSH config
        self.ssh_passphrase = tk.StringVar()
        self.ssh_passphrase.set("your_passphrase_here")
        self.remote_file_path = tk.StringVar()
        self.remote_file_path.set("/opt/sd/chan-log/test/100025451.txt")

        self.card_labels = [[] for _ in range(PLAYER_COUNT + 1)]

        self.load_cards()
        self.create_ui()

    def load_cards(self):
        for cid in CARD_IDS:
            path = os.path.join(CARDS_FOLDER, f"card_{cid}.png")
            if os.path.exists(path):
                img = Image.open(path).resize((CARD_WIDTH, CARD_HEIGHT))
                self.images[cid] = ImageTk.PhotoImage(img)
            else:
                self.images[cid] = None

        self.deck = []
        for cid in CARD_IDS:
            self.deck.extend([cid] * CARD_COUNT_PER_ID)

    def calc_row_col(self, index):
        if index == 0:
            return 1, 8
        result = index % 3, (index - 6) // 3
        return result

    def create_ui(self):
        font_conf = ("JetBrains Mono", 12)

        top_frame = tk.Frame(self.root)
        top_frame.pack(pady=5)

        tk.Label(top_frame, text="Deck Name:", font=font_conf).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.deck_name_var, width=30, font=font_conf).pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="SSH Passphrase:", font=font_conf).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.ssh_passphrase, show="*", width=20, font=font_conf).pack(side=tk.LEFT, padx=5)

        tk.Label(top_frame, text="Remote File Path:", font=font_conf).pack(side=tk.LEFT)
        tk.Entry(top_frame, textvariable=self.remote_file_path, width=40, font=font_conf).pack(side=tk.LEFT, padx=5)

        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=5)

        tk.Button(control_frame, text="Shuffle", command=self.shuffle_deck, font=font_conf).grid(row=0, column=0)
        tk.Button(control_frame, text="Save", command=self.save_to_file, font=font_conf).grid(row=0, column=1)
        tk.Button(control_frame, text="Reset", command=self.reset_all, font=font_conf).grid(row=0, column=2)
        tk.Button(control_frame, text="Upload", command=self.upload_to_server, font=font_conf).grid(row=0, column=3)
        tk.Button(control_frame, text="Load", command=self.load_from_file, font=font_conf).grid(row=0, column=4)

        # Two main horizontal frames
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True)

        # Left: Card Picker
        picker_wrapper = tk.Frame(main_frame)
        picker_wrapper.pack(side=tk.LEFT, padx=10, pady=5)

        selected_display = tk.Frame(picker_wrapper)
        selected_display.pack()
        tk.Label(selected_display, text="CurCard:", font=font_conf).pack()
        self.selected_card_display = tk.Label(selected_display)
        self.selected_card_display.pack(pady=5)
        self.update_selected_display()

        card_picker = tk.Frame(picker_wrapper)
        card_picker.pack()
        tk.Label(card_picker, text="Select Card:", font=font_conf).pack(anchor="w")

        grid_frame = tk.Frame(card_picker)
        grid_frame.pack()
        for i, cid in enumerate(CARD_IDS):
            img = self.images[cid]
            btn = tk.Button(grid_frame, image=img, command=lambda c=cid: self.select_card(c))
            btn.image = img
            row, col = self.calc_row_col(cid)
            btn.grid(row=row, column=col, padx=0, pady=2)

        player_buttons = tk.Frame(picker_wrapper)
        player_buttons.pack(pady=5)
        for i in range(PLAYER_COUNT):
            tk.Button(player_buttons, text=f"+=> {i+1}", command=lambda i=i: self.add_card(i), font=font_conf).pack(side=tk.LEFT, padx=2)
        tk.Button(player_buttons, text="+=>Noc", command=lambda: self.add_card(PLAYER_COUNT), font=font_conf).pack(side=tk.LEFT, padx=2)

        # Right: Card view
        self.card_frame = tk.Frame(main_frame)
        self.card_frame.pack(side=tk.LEFT, padx=10, pady=5, anchor='n')

        self.card_label_frames = []
        for i in range(PLAYER_COUNT):
            frame = tk.Frame(self.card_frame)
            frame.pack(pady=2, anchor='w')
            label = tk.Label(frame, text=f"P{i+1}-0", font=("JetBrains Mono", 12))
            label.pack(side=tk.LEFT)
            self.card_label_frames.append((frame, label))
            self.card_labels[i] = []

        rest_frame = tk.Frame(self.card_frame)
        rest_frame.pack(pady=4, anchor='w')
        label = tk.Label(rest_frame, text="Rest (0)", font=("JetBrains Mono", 12))
        label.pack(side=tk.LEFT)
        self.card_label_frames.append((rest_frame, label))
        self.card_labels[PLAYER_COUNT] = []

        self.render_cards()

    def select_card(self, cid):
        self.selected_card.set(cid)
        self.update_selected_display()

    def update_selected_display(self):
        cid = self.selected_card.get()
        img = self.images.get(cid)
        if img:
            self.selected_card_display.configure(image=img)
            self.selected_card_display.image = img

    def render_cards(self):
        for i in range(PLAYER_COUNT + 1):
            cards = self.players[i] if i < PLAYER_COUNT else self.rest
            frame, count_label = self.card_label_frames[i]
            txt = f"{'Player ' + str(i+1) if i < PLAYER_COUNT else 'Rest'} ({len(cards)})"
            while len(txt) < 12:
                txt = " " + txt
            count_label.config(text=txt)

            for j in range(max(len(cards), len(self.card_labels[i]))):
                if j >= len(self.card_labels[i]):
                    lbl = tk.Label(frame)
                    lbl.pack(side=tk.LEFT, padx=2)
                    self.card_labels[i].append(lbl)

                lbl = self.card_labels[i][j]
                if j < len(cards):
                    cid = cards[j]
                    img = self.images.get(cid)
                    lbl.configure(image=img)
                    lbl.image = img
                    lbl.bind("<Button-1>", lambda e, p=i, c=cid: self.remove_card(p, c))
                    lbl.pack(side=tk.LEFT, padx=0)
                else:
                    lbl.pack_forget()

    def shuffle_deck(self):
        self.reset_all()
        cards = self.deck.copy()
        random.shuffle(cards)

        for i in range(PLAYER_COUNT):
            self.players[i] = sorted(cards[i * CARDS_PER_PLAYER:(i + 1) * CARDS_PER_PLAYER])
        self.rest = sorted(cards[PLAYER_COUNT * CARDS_PER_PLAYER:])
        self.render_cards()

    def remove_card(self, player_index, cid):
        if player_index < PLAYER_COUNT:
            self.players[player_index].remove(cid)
        else:
            self.rest.remove(cid)
        self.render_cards()

    def add_card(self, target_index):
        cid = self.selected_card.get()
        if target_index < PLAYER_COUNT:
            self.players[target_index].append(cid)
            self.players[target_index].sort()
        else:
            self.rest.append(cid)
        self.render_cards()

    def reset_all(self):
        self.players = [[] for _ in range(PLAYER_COUNT)]
        self.rest = []
        self.render_cards()

    def save_to_file(self):
        deck_name = self.deck_name_var.get().strip()
        if not deck_name:
            messagebox.showwarning("Missing Name", "Please enter a deck name.")
            return

        if not os.path.exists("card_deck"):
            os.makedirs("card_deck")
        file_path = os.path.join("card_deck", f"{deck_name}.txt")
        with open(file_path, "w") as f:
            for p in reversed(self.players):
                f.write(",".join(map(str, p)) + "\n")
            f.write(",".join(map(str, self.rest)) + "\n")
        messagebox.showinfo("Saved", f"Card deck saved to {file_path}")

    def load_from_file(self):
        deck_name = self.deck_name_var.get().strip()
        file_path = os.path.join("card_deck", f"{deck_name}.txt")
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"Deck file not found: {file_path}")
            return

        with open(file_path, "r") as f:
            lines = f.read().strip().split("\n")
            if len(lines) < 5:
                messagebox.showerror("Error", "Invalid deck file format.")
                return
            self.players = list(reversed([list(map(int, line.split(","))) for line in lines[:4]]))
            self.rest = list(map(int, lines[4].split(",")))
            self.render_cards()

    def upload_to_server(self):
        remote_path = self.remote_file_path.get().strip()
        passphrase = self.ssh_passphrase.get().strip()
        deck_name = self.deck_name_var.get().strip()

        if not remote_path or not passphrase or not deck_name:
            messagebox.showwarning("Missing Info", "Please enter deck name, SSH passphrase, and remote path.")
            return

        local_content = "\n".join([",".join(map(str, p)) for p in reversed(self.players)] + [",".join(map(str, self.rest))]) + "\n"

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname="dev.sandinhstudio.com", username="nghiavt", key_filename=os.path.expanduser("~/.ssh/id_rsa"), passphrase=passphrase)

            sftp = ssh.open_sftp()
            with sftp.file(remote_path, 'w') as f:
                f.write(local_content)
            sftp.close()
            ssh.close()

            messagebox.showinfo("Uploaded", f"Deck uploaded to {remote_path}")
        except Exception as e:
            messagebox.showerror("Upload Failed", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = CardDeckTool(root)
    root.mainloop()
