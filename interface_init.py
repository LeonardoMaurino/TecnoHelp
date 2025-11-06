import tkinter as tk
from tkinter import scrolledtext, messagebox
import subprocess
import threading
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FLASK_SCRIPT = os.path.join(BASE_DIR, "chat_bot.py")
BAILEYS_SCRIPT = os.path.join(BASE_DIR, "baileys", "main.js")


class InicializadorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Inicializador - Chatbot Técnico")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e")

        self.flask_process = None

       
        tk.Label(
            root, text="Assistente Técnico - Inicialização",
            font=("Segoe UI", 16, "bold"), fg="white", bg="#1e1e1e"
        ).pack(pady=10)

        
        self.log_area = scrolledtext.ScrolledText(
            root, width=85, height=22, bg="#252526", fg="#dcdcdc", insertbackground="white"
        )
        self.log_area.pack(padx=10, pady=10)
        self.log_area.insert(tk.END, "😺 Pronto para iniciar.\n")

        # Botões
        frame_btn = tk.Frame(root, bg="#1e1e1e")
        frame_btn.pack(pady=10)

        self.btn_iniciar = tk.Button(
            frame_btn, text="▶️ Iniciar Assistente", command=self.iniciar,
            bg="#2ecc71", fg="white", font=("Segoe UI", 12, "bold"), width=20
        )
        self.btn_iniciar.pack(side=tk.LEFT, padx=10)

        self.btn_parar = tk.Button(
            frame_btn, text="⏹️ Parar", command=self.parar,
            bg="#e74c3c", fg="white", font=("Segoe UI", 12, "bold"), width=10
        )
        self.btn_parar.pack(side=tk.LEFT, padx=10)

   
    def iniciar(self):
        if self.flask_process:
            messagebox.showinfo("Aviso", "Os processos já estão em execução.")
            return

        self.log("🚀 Iniciando Flask e Baileys...")

        
        threading.Thread(target=self.iniciar_flask, daemon=True).start()
        threading.Thread(target=self.iniciar_baileys, daemon=True).start()

    
    def iniciar_flask(self):
        try:
            self.log("🔃 Iniciando servidor Flask...")
            self.flask_process = subprocess.Popen(
                [sys.executable, FLASK_SCRIPT],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in self.flask_process.stdout:
                self.log(f"[FLASK] {line.strip()}")
        except Exception as e:
            self.log(f"❌ Erro ao iniciar Flask: {e}")

    # =============================
    # Inicia o QR code Baileys (em terminal separado)
    # =============================
    def iniciar_baileys(self):
        try:
            self.log("🔃 Abrindo bot Baileys em um terminal separado...")

            
            cmd = f'start "Baileys - WhatsApp Bot" cmd /k node "{BAILEYS_SCRIPT}"'

            
            subprocess.Popen(cmd, shell=True)

            self.log("✅ Terminal do Baileys aberto com sucesso. Escaneie o QR code lá.")
        except Exception as e:
            self.log(f"❌ Erro ao iniciar Baileys: {e}")

    
    def parar(self):
        if self.flask_process:
            self.flask_process.terminate()
            self.log("🛑 Flask encerrado.")
            self.flask_process = None
        self.log("🛑 Se desejar encerrar o Baileys, feche o terminal manualmente.")

    # =============================
    # Função auxiliar de log
    # =============================
    def log(self, texto):
        self.log_area.insert(tk.END, texto + "\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()


if __name__ == "__main__":
    root = tk.Tk()
    app = InicializadorApp(root)
    root.mainloop()
