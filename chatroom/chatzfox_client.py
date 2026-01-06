import socket
import threading
import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES
from PIL import Image, ImageTk
import os
import webbrowser
import re

SERVER_IP = "192.168.56.1"
PORT = 5555
BUFFER_SIZE = 4096

class ChatZFoxClient:
    def __init__(self, root):
        self.root = root
        self.root.title("ChatZFox")
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.images = []  # Referenzen für Bilder, damit Tkinter sie nicht löscht
        self.mode = "light"
        self.login_screen()

    # ===== Login =====
    def login_screen(self):
        self.clear()
        tk.Label(self.root, text="Username").pack(pady=5)
        self.name_entry = tk.Entry(self.root)
        self.name_entry.pack()
        tk.Button(self.root, text="Join ChatZFox", command=self.connect).pack(pady=5)
        self.name_entry.focus_set()

    # ===== Connect =====
    def connect(self):
        self.username = self.name_entry.get().strip()
        if not self.username:
            return
        try:
            self.sock.connect((SERVER_IP, PORT))
        except Exception as e:
            tk.messagebox.showerror("Fehler", f"Verbindung fehlgeschlagen:\n{e}")
            return

        self.build_chat()
        threading.Thread(target=self.receive_loop, daemon=True).start()
        self.sock.send(f"MSG:{self.username} joined the chat\n".encode())
        self.entry.focus_set()

    # ===== Chat GUI =====
    def build_chat(self):
        self.clear()
        frame = tk.Frame(self.root)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.scrollbar = tk.Scrollbar(frame)
        self.scrollbar.pack(side="right", fill="y")

        self.chat = tk.Text(frame, state="disabled", width=70, height=20, yscrollcommand=self.scrollbar.set, wrap="word")
        self.chat.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.chat.yview)

        self.entry = tk.Entry(self.root)
        self.entry.pack(fill="x", padx=5, pady=5)
        self.entry.bind("<Return>", lambda e: self.send_message())
        self.entry.focus_set()

        self.drop_area = tk.Label(self.root, text="⬇ Datei hier reinziehen ⬇", relief="ridge", height=3)
        self.drop_area.pack(fill="x", padx=5, pady=5)
        self.drop_area.drop_target_register(DND_FILES)
        self.drop_area.dnd_bind("<<Drop>>", self.drop_file)

        emoji_frame = tk.Frame(self.root)
        emoji_frame.pack(fill="x", padx=5, pady=5)
        for emoji in ["😊","😂","❤️","👍","😎","🤔"]:
            tk.Button(emoji_frame, text=emoji, command=lambda e=emoji: self.insert_emoji(e)).pack(side="left")
        tk.Button(emoji_frame, text="Toggle Light/Dark", command=self.toggle_mode).pack(side="right")

        self.apply_mode()

    # ===== Emojis =====
    def insert_emoji(self, emoji):
        self.entry.insert(tk.END, emoji)
        self.entry.focus_set()

    # ===== Senden =====
    def send_message(self):
        msg = self.entry.get()
        if msg:
            try:
                self.sock.send(f"MSG:{self.username}: {msg}\n".encode())
            except Exception as e:
                self.show_text(f"❌ Fehler beim Senden: {e}")
            self.entry.delete(0, tk.END)
            self.entry.focus_set()

    # ===== Drag & Drop Dateien senden =====
    def drop_file(self, event):
        paths = self.root.splitlist(event.data)
        for path in paths:
            filename = os.path.basename(path)
            try:
                with open(path, "rb") as f:
                    data = f.read()
                header = f"FILE:{filename}|{len(data)}\n".encode()
                self.sock.send(header + data)
            except Exception as e:
                self.show_text(f"❌ Fehler beim Senden von {filename}: {e}")

    # ===== Empfang =====
    def receive_loop(self):
        buffer = b""
        while True:
            try:
                data = self.sock.recv(BUFFER_SIZE)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    header, buffer = buffer.split(b"\n",1)
                    if header.startswith(b"MSG:"):
                        self.insert_linkable_text(header[4:].decode())
                    elif header.startswith(b"FILE:"):
                        header_parts = header[5:].decode().split("|")
                        if len(header_parts)!=2:
                            continue
                        filename, size = header_parts
                        size = int(size)
                        while len(buffer)<size:
                            buffer += self.sock.recv(BUFFER_SIZE)
                        filedata, buffer = buffer[:size], buffer[size:]
                        self.handle_file(filename, filedata)
            except Exception as e:
                self.show_text(f"❌ Fehler beim Empfangen: {e}")
                break

    # ===== Text anzeigen + Auto-Scroll =====
    def show_text(self, text):
        self.chat.config(state="normal")
        self.chat.insert(tk.END, text+"\n")
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    # ===== Links klickbar =====
    def insert_linkable_text(self, text):
        self.chat.config(state="normal")
        parts = re.split(r"(https?://[^\s]+)", text)
        for idx, part in enumerate(parts):
            if re.match(r"https?://[^\s]+", part):
                tag = f"link_{self.chat.index(tk.END)}_{idx}"
                start_index = self.chat.index(tk.END)
                self.chat.insert(tk.END, part)
                end_index = self.chat.index(tk.END)
                self.chat.tag_add(tag, start_index, end_index)
                self.chat.tag_config(tag, foreground="blue", underline=1)
                self.chat.tag_bind(tag, "<Button-1>", lambda e, url=part: webbrowser.open(url))
            else:
                self.chat.insert(tk.END, part)
        self.chat.insert(tk.END,"\n")
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    # ===== Dateien behandeln =====
    def handle_file(self, filename, data):
        temp_dir = os.path.join(os.getcwd(), "_downloads")
        os.makedirs(temp_dir, exist_ok=True)
        path = os.path.join(temp_dir, filename)
        with open(path,"wb") as f:
            f.write(data)

        if filename.lower().endswith((".png",".jpg",".jpeg",".gif")):
            self.show_image(filename, path)
        else:
            self.show_download(filename, path)

    # ===== Bilder anzeigen + Download =====
    def show_image(self, filename, path):
        img = Image.open(path)
        if img.mode!="RGB":
            img = img.convert("RGB")
        img.thumbnail((250,250))
        photo = ImageTk.PhotoImage(img)
        self.images.append(photo)

        def save_img():
            dst = filedialog.asksaveasfilename(initialfile=filename)
            if dst:
                with open(path,"rb") as fsrc:
                    with open(dst,"wb") as fdst:
                        fdst.write(fsrc.read())

        self.chat.config(state="normal")
        self.chat.image_create(tk.END, image=photo)
        self.chat.insert(tk.END, f"\n📷 {filename} gesendet ")
        self.chat.window_create(tk.END, window=tk.Button(self.chat, text="DOWNLOAD", command=save_img))
        self.chat.insert(tk.END, "\n\n")
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    # ===== Andere Dateien mit Download =====
    def show_download(self, filename, path):
        def save_file():
            dst = filedialog.asksaveasfilename(initialfile=filename)
            if dst:
                with open(path,"rb") as fsrc:
                    with open(dst,"wb") as fdst:
                        fdst.write(fsrc.read())

        self.chat.config(state="normal")
        self.chat.insert(tk.END, f"\n📁 {filename} gesendet ")
        self.chat.window_create(tk.END, window=tk.Button(self.chat, text="DOWNLOAD", command=save_file))
        self.chat.insert(tk.END, "\n\n")
        self.chat.config(state="disabled")
        self.chat.see(tk.END)

    # ===== Hell/Dunkelmodus =====
    def toggle_mode(self):
        self.mode = "dark" if self.mode=="light" else "light"
        self.apply_mode()

    def apply_mode(self):
        if self.mode=="light":
            bg, fg = "white","black"
        else:
            bg, fg = "#222222","white"
        self.chat.config(bg=bg, fg=fg, insertbackground=fg)
        self.entry.config(bg=bg, fg=fg, insertbackground=fg)
        self.drop_area.config(bg=bg, fg=fg)

    # ===== Helper =====
    def clear(self):
        for w in self.root.winfo_children():
            w.destroy()

# ===== MAIN =====
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ChatZFoxClient(root)
    root.mainloop()
