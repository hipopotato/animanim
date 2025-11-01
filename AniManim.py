import tkinter as tk
from tkinter import scrolledtext, Toplevel, filedialog, messagebox, Text, Scrollbar, Frame
import subprocess
import os
import shutil
import re
import threading
import webbrowser
import sys
import locale # Import locale

# --- (Estilos dos botões inferiores) ---
BTN_STYLE = {
    "bg": "#FFFFFF", "fg": "#016F01", "activebackground": "#F0FFF0",
    "activeforeground": "#016F01", "relief": "flat", "highlightthickness": 2,
    "highlightbackground": "#016F01", "highlightcolor": "#00AF00",
    "font": ("Arial", 10, "bold"), "pady": 4, "padx": 15
}
RIGHT_BTN_STYLE = BTN_STYLE.copy()
RIGHT_BTN_STYLE["pady"] = 4; RIGHT_BTN_STYLE["padx"] = 10
RIGHT_BTN_STYLE["font"] = ("Arial", 9, "bold"); RIGHT_BTN_STYLE["highlightthickness"] = 1
RENDER_BTN_STYLE = BTN_STYLE.copy()
RENDER_BTN_STYLE["pady"] = 4; RENDER_BTN_STYLE["font"] = ("Arial", 12, "bold")

# --- (Estilos dos botões superiores) ---
TOP_BTN_STYLE = {
    "font": ("Arial", 10, "bold"), "bg": "#505050", "fg": "white",
    "activebackground": "#707070", "relief": "flat", "pady": 0, "padx": 5
}

# --- (Estilo dos botões flutuantes) ---
IN_WIDGET_BTN_STYLE = {
    "font": ("Arial", 8, "bold"), "bg": "#333333", "fg": "white",
    "activebackground": "#707070", "relief": "flat", "pady": 0,
    "padx": 4, "bd": 0, "highlightthickness": 0
}


# --- (Cores) ---
BG_COLOR = "#2E2E2E"
TEXT_BG_COLOR = "#404040"
FG_COLOR = "white"
LINE_NUM_BG = "#333333"
LINE_NUM_FG = "#AAAAAA"
HIGHLIGHT_BG = "#FFFF00"
HIGHLIGHT_FG = "#000000"

### FUNÇÃO AUXILIAR PARA ENCONTRAR ARQUIVOS EMPACOTADOS ###
def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ManimApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AniManim: Animações com Manim")
        self.geometry("700x700")
        self.configure(bg=BG_COLOR)

        icon_path = None
        try:
            icon_path = resource_path('meu_icone.ico')
            self.iconbitmap(icon_path)
        except tk.TclError as e: print(f"ERRO Tcl/Tk ao definir ícone '{icon_path}': {e}")
        except Exception as e: print(f"ERRO inesperado ao definir ícone '{icon_path}': {e}")

        # --- Variáveis para a função Localizar ---
        self._find_window = None
        self._find_entry = None
        self._find_last_index = "1.0"

        # --- Variável para o processo Manim ---
        self.manim_process = None

        # --- Barra Superior ---
        top_bar = Frame(self, bg=BG_COLOR); top_bar.pack(side="top", fill="x", pady=5)
        self.clear_btn = tk.Button(top_bar, text=" Limpar ", **TOP_BTN_STYLE, command=self.clear_code); self.clear_btn.pack(side="left", padx=10)
        header = tk.Label(top_bar, text="Cole seu código Manim abaixo:", fg=FG_COLOR, bg=BG_COLOR, font=("Arial", 12)); header.pack(side="left", fill="x", expand=True, padx=10)
        self.quality_options = {"Baixa (480p)": "-ql", "Média (720p)": "-qm", "Alta (1080p)": "-qh", "4K (2160p)": "-qk"}
        self.selected_quality_flag = tk.StringVar(self); self.selected_quality_flag.set("Baixa (480p)")
        style = TOP_BTN_STYLE.copy(); style["pady"] = 2; style["width"] = 12; style["indicatoron"] = 0
        self.quality_menu = tk.OptionMenu(top_bar, self.selected_quality_flag, *self.quality_options.keys())
        self.quality_menu.config(**style); self.quality_menu["menu"].config(bg=BG_COLOR, fg=FG_COLOR, activebackground="#707070", font=("Arial", 10))
        self.quality_menu.pack(side="right", padx=5)
        self.info_btn = tk.Button(top_bar, text=" i ", **TOP_BTN_STYLE, command=self.show_info); self.info_btn.pack(side="right", padx=10)

        # --- Barra Inferior ---
        bottom_bar = Frame(self, bg=BG_COLOR); bottom_bar.pack(side="bottom", fill="x", pady=(5, 10))
        left_frame = Frame(bottom_bar, bg=BG_COLOR); left_frame.pack(side="left", expand=True, fill="both", padx=10)
        right_frame = Frame(bottom_bar, bg=BG_COLOR); right_frame.pack(side="right", fill="y", padx=10)
        self.render_btn = tk.Button(left_frame, text="Renderizar", **RENDER_BTN_STYLE, command=self.start_manim_thread); self.render_btn.pack(expand=True, fill="both")
        self.save_code_btn = tk.Button(right_frame, text="Salvar Código", **RIGHT_BTN_STYLE, command=self.save_code); self.save_code_btn.pack(fill="x", expand=True, pady=(0, 3))
        self.save_video_btn = tk.Button(right_frame, text="Salvar Vídeo", **RIGHT_BTN_STYLE, command=self.save_video); self.save_video_btn.pack(fill="x", expand=True)

        # --- Console ---
        console_frame = Frame(self, bg=TEXT_BG_COLOR); console_frame.pack(side="bottom", fill="x", padx=10, pady=(0, 5))
        console_scrollbar = Scrollbar(console_frame, orient="vertical")
        self.console_output = Text(console_frame, height=8, bg=TEXT_BG_COLOR, fg=FG_COLOR, font=("Courier New", 9),
                                    relief="flat", bd=0, yscrollcommand=console_scrollbar.set, wrap="word")
        console_scrollbar.config(command=self.console_output.yview)
        console_scrollbar.pack(side="right", fill="y")
        self.console_output.pack(expand=True, fill="both")
        self.console_output.tag_config("info", foreground="white"); self.console_output.tag_config("success", foreground="light green"); self.console_output.tag_config("error", foreground="#FF6B6B")
        self.console_output.config(state="disabled")

        ### NOVO: Botão Forçar Parada ###
        self.force_stop_btn = tk.Button(console_frame, text="Forçar Parada",
                                        **IN_WIDGET_BTN_STYLE,
                                        command=self._force_stop_manim,
                                        state="disabled") # Começa desabilitado
        # Posiciona à esquerda do botão Copiar Mensagem
        self.force_stop_btn.place(relx=1.0, rely=1.0, anchor='se', x=-140, y=-5) # Ajuste o 'x' se necessário

        # Botão Copiar Mensagem (posição mantida relativa à direita)
        self.copy_console_btn = tk.Button(console_frame, text="Copiar Mensagem", **IN_WIDGET_BTN_STYLE, command=self.copy_console_message)
        self.copy_console_btn.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-5)


        # --- Editor de Código com Números de Linha ---
        code_editor_frame = Frame(self, bg=TEXT_BG_COLOR)
        code_editor_frame.pack(pady=5, padx=10, expand=True, fill="both")
        self.line_numbers = Text(code_editor_frame, width=4, padx=3, takefocus=0, bd=0, bg=LINE_NUM_BG, fg=LINE_NUM_FG, state='disabled', wrap='none', font=("Courier New", 10))
        self.line_numbers.pack(side="left", fill="y")
        code_scrollbar = Scrollbar(code_editor_frame, orient="vertical")
        code_scrollbar.pack(side="right", fill="y")
        self.code_text = Text(code_editor_frame, width=80, bg=TEXT_BG_COLOR, fg=FG_COLOR, insertbackground=FG_COLOR, undo=True, relief="flat", bd=0, yscrollcommand=code_scrollbar.set, wrap="word", font=("Courier New", 10))
        self.code_text.pack(side="left", expand=True, fill="both")
        code_scrollbar.config(command=self._scroll_text)
        self.line_numbers.config(yscrollcommand=code_scrollbar.set)
        self.code_text.tag_configure("find_highlight", background=HIGHLIGHT_BG, foreground=HIGHLIGHT_FG)
        # Bindings para atualizar linhas
        self.code_text.bind("<KeyPress>", self._on_key_press_release); self.code_text.bind("<KeyRelease>", self._on_key_press_release)
        self.code_text.bind("<MouseWheel>", self._on_scroll); self.code_text.bind("<Button-4>", self._on_scroll); self.code_text.bind("<Button-5>", self._on_scroll)
        self.code_text.bind("<<Paste>>", self._on_key_press_release); self.code_text.bind("<<Cut>>", self._on_key_press_release)
        self.code_text.bind("<<Undo>>", self._on_key_press_release); self.code_text.bind("<<Redo>>", self._on_key_press_release)
        self._update_line_numbers() # Desenha linhas iniciais

        # --- Botões Flutuantes no Editor ---
        self.find_btn = tk.Button(code_editor_frame, text="Localizar", **IN_WIDGET_BTN_STYLE, command=self._open_find_dialog); self.find_btn.place(relx=0.0, rely=1.0, anchor='sw', x=5, y=-5)
        self.paste_code_btn = tk.Button(code_editor_frame, text="Colar Código", **IN_WIDGET_BTN_STYLE, command=self.paste_code); self.paste_code_btn.place(relx=1.0, rely=1.0, anchor='se', x=-115, y=-5)
        self.copy_code_btn = tk.Button(code_editor_frame, text="Copiar Código", **IN_WIDGET_BTN_STYLE, command=self.copy_code); self.copy_code_btn.place(relx=1.0, rely=1.0, anchor='se', x=-20, y=-5)

    # --- Funções para Números de Linha ---
    def _scroll_text(self, *args):
        self.code_text.yview(*args); self.line_numbers.yview(*args)
        self._update_line_numbers(); return "break"
    def _on_scroll(self, event):
        if event.num == 4 or event.delta > 0: delta = -1
        elif event.num == 5 or event.delta < 0: delta = 1
        else: return
        self.code_text.yview_scroll(delta, "units"); self.line_numbers.yview_scroll(delta, "units")
        self._update_line_numbers(); return "break"
    def _on_key_press_release(self, event=None): self.after_idle(self._update_line_numbers)
    def _update_line_numbers(self, event=None):
        self.line_numbers.config(state='normal'); self.line_numbers.delete('1.0', 'end')
        total_lines = int(self.code_text.index('end-1c').split('.')[0])
        line_count_string = "\n".join(str(i) for i in range(1, total_lines + 1))
        if line_count_string: self.line_numbers.insert('1.0', line_count_string)
        scroll_fraction_top, _ = self.code_text.yview()
        self.line_numbers.yview_moveto(scroll_fraction_top)
        self.line_numbers.config(state='disabled')

    # --- Funções para Localizar ---
    def _open_find_dialog(self):
        if self._find_window is not None and self._find_window.winfo_exists(): self._find_window.lift(); return
        self._find_window = Toplevel(self); self._find_window.title("Localizar"); self._find_window.geometry("300x100")
        self._find_window.resizable(False, False); self._find_window.transient(self)
        self._find_window.update_idletasks(); x = self.winfo_x() + (self.winfo_width() - self._find_window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - self._find_window.winfo_height()) // 2; self._find_window.geometry(f"+{x}+{y}")
        find_label = tk.Label(self._find_window, text="Localizar:"); find_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self._find_entry = tk.Entry(self._find_window, width=30); self._find_entry.grid(row=0, column=1, padx=5, pady=5, columnspan=2); self._find_entry.focus_set()
        self._find_entry.bind("<Return>", lambda event: self._find_text())
        find_next_btn = tk.Button(self._find_window, text="Localizar Próximo", command=self._find_text); find_next_btn.grid(row=1, column=1, padx=5, pady=10, sticky="e")
        cancel_btn = tk.Button(self._find_window, text="Cancelar", command=self._close_find_dialog); cancel_btn.grid(row=1, column=2, padx=5, pady=10, sticky="e")
        self._find_window.protocol("WM_DELETE_WINDOW", self._close_find_dialog)
    def _close_find_dialog(self):
        if self._find_window:
            self.code_text.tag_remove("find_highlight", "1.0", tk.END); self._find_last_index = "1.0"
            self._find_window.destroy(); self._find_window = None
    def _find_text(self, wrap=True):
        if not self._find_window or not self._find_entry: return
        search_term = self._find_entry.get();
        if not search_term: return
        self.code_text.tag_remove("find_highlight", "1.0", tk.END)
        start_index = self._find_last_index
        pos = self.code_text.search(search_term, start_index, tk.END, nocase=True)
        if pos:
            end_index = f"{pos}+{len(search_term)}c"; self.code_text.tag_add("find_highlight", pos, end_index)
            self.code_text.see(pos); self._find_last_index = end_index; self._find_window.lift()
        elif wrap and start_index != "1.0": self._find_last_index = "1.0"; self._find_text(wrap=False)
        else: messagebox.showinfo("Localizar", f"Não foi possível encontrar '{search_term}'", parent=self._find_window); self._find_last_index = "1.0"

    # --- Funções Anteriores ---

    ### FUNÇÃO show_info ATUALIZADA (com o texto de 'ss - Copia.py') ###
    def show_info(self):
        info_window = Toplevel(self)
        info_window.title("Informações")
        info_window.configure(bg=BG_COLOR)
        info_window.geometry("600x700") 
        info_window.transient(self)
        info_window.grab_set()

        text_frame = tk.Frame(info_window, bg=BG_COLOR)
        text_frame.pack(expand=True, fill="both", padx=10, pady=(10, 0))

        info_text_widget = tk.Text(text_frame, wrap="word", 
                                   bg=TEXT_BG_COLOR, fg=FG_COLOR, 
                                   padx=15, pady=15, 
                                   font=("Arial", 10),
                                   relief="flat", borderwidth=0)
        info_text_widget.pack(expand=True, fill="both")

        def open_link(url):
            webbrowser.open_new(url)

        base_font = ("Arial", 10)
        h1_font = ("Arial", 13, "bold")
        info_text_widget.tag_config("h1", font=h1_font, spacing1=5, spacing3=10)
        bold_font = ("Arial", 10, "bold")
        info_text_widget.tag_config("bold", font=bold_font)
        link_color = "#61AFEF"
        info_text_widget.tag_config("link", foreground=link_color, underline=True)
        info_text_widget.tag_bind("link", "<Enter>", 
                                  lambda e: info_text_widget.config(cursor="hand2"))
        info_text_widget.tag_bind("link", "<Leave>", 
                                  lambda e: info_text_widget.config(cursor=""))

        info_text_widget.config(state="normal")
        info_text_widget.insert(tk.END, "Sobre esta Aplicação\n", "h1")
        info_text_widget.insert(tk.END, 
            "Este programa foi desenvolvido com o auxílio de Inteligência Artificial (IA) "
            "e será utilizado como produto educacional em uma dissertação de mestrado do PROFMAT.\n\n")
        
        info_text_widget.insert(tk.END, "Como foi criado?\n", "bold")
        info_text_widget.insert(tk.END, 
            "O desenvolvimento foi um processo iterativo... (a IA gerou, refinou e depurou o código Python...)\n\n")

        info_text_widget.insert(tk.END, "Como Usar\n", "h1")
        info_text_widget.insert(tk.END, 
            "1.  **Cole o código:** Insira seu script Manim na caixa de texto.\n"
            "2.  **Qualidade:** Escolha a qualidade da animação no menu (ao lado do 'i').\n"
            "3.  **Renderizar:** Executa o código e abre o player de vídeo.\n"
            "4.  **Salvar Vídeo:** Este botão NÃO renderiza novamente. Ele apenas permite que você salve o vídeo mais recente (que já foi renderizado) em um local de sua escolha.\n\n"
            "**Importante:** Cada vez que você clica em 'Renderizar', o arquivo de vídeo é salvo automaticamente em uma pasta chamada 'media' (criada dentro da pasta deste aplicativo). O botão 'Salvar Vídeo' serve apenas para copiar esse arquivo para outro lugar (ex: sua Área de Trabalho).\n\n"
            "5.  **Console:** Mostra o status da renderização ou mensagens de erro.\n\n")

        info_text_widget.insert(tk.END, "Requisitos de Instalação\n", "h1")
        info_text_widget.insert(tk.END, 
            "Para que este aplicativo possa renderizar...:\n\n")

        info_text_widget.insert(tk.END, "1.  ", base_font)
        info_text_widget.insert(tk.END, "Python 3:", "bold")
        info_text_widget.insert(tk.END, " A linguagem base do aplicativo.\n    * Link: ")
        info_text_widget.insert(tk.END, "https://www.python.org/", ("link", "link_py"))
        info_text_widget.tag_bind("link_py", "<Button-1>", lambda e: open_link("https://www.python.org/"))

        info_text_widget.insert(tk.END, "\n\n2.  ", base_font)
        info_text_widget.insert(tk.END, "Manim (Community Edition):", "bold")
        info_text_widget.insert(tk.END, "\n    * Link: ")
        info_text_widget.insert(tk.END, "https://www.manim.community/", ("link", "link_manim"))
        info_text_widget.tag_bind("link_manim", "<Button-1>", lambda e: open_link("https://www.manim.community/"))
        
        info_text_widget.insert(tk.END, "\n\n3.  ", base_font)
        info_text_widget.insert(tk.END, "LaTeX (para Windows):", "bold")
        info_text_widget.insert(tk.END, " Essencial para renderizar textos e fórmulas.\n")
        
        info_text_widget.insert(tk.END, "    (Obs: Códigos que animam apenas formas, sem `Text` ou `MathTex`, podem funcionar sem o LaTeX.)\n")
        
        info_text_widget.insert(tk.END, "    * Windows: ")
        info_text_widget.insert(tk.END, "https://miktex.org/", ("link", "link_miktex"))
        info_text_widget.tag_bind("link_miktex", "<Button-1>", lambda e: open_link("https://miktex.org/"))
        
        info_text_widget.insert(tk.END, "\n\n4.  ", base_font)
        info_text_widget.insert(tk.END, "FFmpeg:", "bold")
        info_text_widget.insert(tk.END, "\n    * Link: ")
        info_text_widget.insert(tk.END, "https://ffmpeg.org/download.html", ("link", "link_ffmpeg"))
        info_text_widget.tag_bind("link_ffmpeg", "<Button-1>", lambda e: open_link("https://ffmpeg.org/download.html"))

        info_text_widget.config(state="disabled") 

        dep_frame = tk.Frame(info_window, bg=BG_COLOR, pady=10)
        dep_frame.pack(fill="x", side="bottom")

        labels_dict = {}
        grid_frame = tk.Frame(dep_frame, bg=BG_COLOR)
        grid_frame.pack()
        status_font = ("Courier New", 10)
        
        tk.Label(grid_frame, text="Python:", font=status_font, bg=BG_COLOR, fg=FG_COLOR).grid(row=0, column=0, sticky="w", padx=5)
        labels_dict["py"] = tk.Label(grid_frame, text="--", font=status_font, bg=BG_COLOR, fg="yellow")
        labels_dict["py"].grid(row=0, column=1, sticky="w", padx=5)
        
        tk.Label(grid_frame, text="Manim:", font=status_font, bg=BG_COLOR, fg=FG_COLOR).grid(row=1, column=0, sticky="w", padx=5)
        labels_dict["manim"] = tk.Label(grid_frame, text="--", font=status_font, bg=BG_COLOR, fg="yellow")
        labels_dict["manim"].grid(row=1, column=1, sticky="w", padx=5)

        tk.Label(grid_frame, text="LaTeX:", font=status_font, bg=BG_COLOR, fg=FG_COLOR).grid(row=2, column=0, sticky="w", padx=5)
        labels_dict["latex"] = tk.Label(grid_frame, text="--", font=status_font, bg=BG_COLOR, fg="yellow")
        labels_dict["latex"].grid(row=2, column=1, sticky="w", padx=5)

        tk.Label(grid_frame, text="FFmpeg:", font=status_font, bg=BG_COLOR, fg=FG_COLOR).grid(row=3, column=0, sticky="w", padx=5)
        labels_dict["ffmpeg"] = tk.Label(grid_frame, text="--", font=status_font, bg=BG_COLOR, fg="yellow")
        labels_dict["ffmpeg"].grid(row=3, column=1, sticky="w", padx=5)

        check_deps_btn = tk.Button(dep_frame, text="Verificar Dependências", 
                                   **RIGHT_BTN_STYLE, 
                                   command=lambda: self.start_dependency_check(check_deps_btn, labels_dict, info_window))
        check_deps_btn.pack(pady=(10,0))
        
        close_btn = tk.Button(dep_frame, text="Fechar", 
                              command=info_window.destroy, 
                              **RIGHT_BTN_STYLE)
        close_btn.pack(pady=(5, 10))
        
        info_window.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - info_window.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - info_window.winfo_height()) // 2
        info_window.geometry(f"+{x}+{y}")
        
        self.start_dependency_check(check_deps_btn, labels_dict, info_window)

    def update_status_label(self, window, label, text, color):
        try:
            if window.winfo_exists() and label.winfo_exists(): label.config(text=text, fg=color)
        except tk.TclError: pass
    def start_dependency_check(self, button, labels_dict, window):
        button.config(state="disabled", text="Verificando...")
        for label in labels_dict.values(): self.update_status_label(window, label, "Verificando...", "yellow")
        thread = threading.Thread(target=self._run_dependency_check, args=(button, labels_dict, window), daemon=True); thread.start()
    def _run_dependency_check(self, button, labels, window):
        py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"; self.after(0, self.update_status_label, window, labels["py"], f"OK (v{py_version})", "light green")
        if shutil.which("manim"): self.after(0, self.update_status_label, window, labels["manim"], "OK", "light green")
        else: self.after(0, self.update_status_label, window, labels["manim"], "Não encontrado", "#FF6B6B")
        if shutil.which("latex"): self.after(0, self.update_status_label, window, labels["latex"], "OK", "light green")
        else: self.after(0, self.update_status_label, window, labels["latex"], "Não encontrado", "#FF6B6B")
        if shutil.which("ffmpeg"): self.after(0, self.update_status_label, window, labels["ffmpeg"], "OK", "light green")
        else: self.after(0, self.update_status_label, window, labels["ffmpeg"], "Não encontrado", "#FF6B6B")
        try:
            if window.winfo_exists() and button.winfo_exists(): self.after(0, button.config, {"state": "normal", "text": "Verificar Novamente"})
        except tk.TclError: pass

    def clear_code(self): self.code_text.delete("1.0", tk.END); self._update_line_numbers()
    def update_console(self, message, level="info"):
        self.console_output.config(state="normal"); self.console_output.delete("1.0", tk.END)
        self.console_output.insert(tk.END, message, level); self.console_output.see(tk.END)
        self.console_output.config(state="disabled")
    def copy_code(self):
        code = self.code_text.get("1.0", tk.END)
        if not code.strip(): self.update_console("Não há código para copiar.", "info"); return
        try: self.clipboard_clear(); self.clipboard_append(code); self.update_idletasks(); self.update_console("Código copiado!", "success")
        except tk.TclError: self.update_console("Não foi possível acessar a área de transferência.", "error")
        except Exception as e: self.update_console(f"Erro ao copiar: {e}", "error")
    def copy_console_message(self):
        self.console_output.config(state="normal"); message = self.console_output.get("1.0", tk.END); self.console_output.config(state="disabled")
        if not message.strip(): self.copy_console_btn.config(text="Vazio!", state="disabled"); self.after(1000, lambda: self.copy_console_btn.config(text="Copiar Mensagem", state="normal")); return
        try: self.clipboard_clear(); self.clipboard_append(message); self.update_idletasks(); self.copy_console_btn.config(text="Copiado!", state="disabled"); self.after(1500, lambda: self.copy_console_btn.config(text="Copiar Mensagem", state="normal"))
        except Exception as e: self.update_console(f"Erro ao copiar mensagem: {e}", "error")
    def paste_code(self):
        try:
            clipboard_content = self.clipboard_get()
            if clipboard_content: self.code_text.delete("1.0", tk.END); self.code_text.insert("1.0", clipboard_content); self.update_console("Código colado.", "info"); self._update_line_numbers()
            else: self.update_console("Área de transferência vazia.", "info")
        except tk.TclError: self.update_console("Não há texto na área de transferência ou erro.", "error")
        except Exception as e: self.update_console(f"Erro ao colar: {e}", "error")
    def save_code(self):
        code = self.code_text.get("1.0", tk.END)
        if not code.strip(): messagebox.showwarning("Aviso", "Não há código para salvar."); return
        save_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Files", "*.py")], title="Salvar código como...", initialfile="meu_codigo_manim.py")
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f: f.write(code)
                self.update_console(f"Código salvo em: {save_path}", "success")
            except Exception as e: self.update_console(f"Erro ao salvar código: {e}", "error")
    def _get_scene_name(self, code):
        match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(\s*([a-zA-Z0-9_.]*Scene)\s*\)\s*:", code)
        if match: return match.group(1)
        match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\(", code)
        if match: self.update_console("Aviso: Não foi possível detectar a cena principal...", "info"); return match.group(1)
        return None

    def set_buttons_state(self, state, text_play="Renderizar", text_save="Salvar Vídeo"):
        # Determina o estado do botão Forçar Parada (habilitado apenas durante a renderização)
        stop_state = "normal" if state == "disabled" else "disabled"

        self.render_btn.config(state=state, text=text_play); self.save_video_btn.config(state=state, text=text_save)
        self.save_code_btn.config(state=state); self.copy_code_btn.config(state=state)
        self.copy_console_btn.config(state=state); self.clear_btn.config(state=state)
        self.quality_menu.config(state=state); self.paste_code_btn.config(state=state)
        self.find_btn.config(state=state)
        self.force_stop_btn.config(state=stop_state) # Controla o botão Forçar Parada
        self.update_idletasks()

    def start_manim_thread(self, play=True):
        code = self.code_text.get("1.0", tk.END)
        if not code.strip(): self.update_console("Erro: O campo de código está vazio.", "error"); return
        scene_name = self._get_scene_name(code)
        if not scene_name: self.update_console("Erro: Não foi possível encontrar o nome da Cena...", "error"); return
        quality_name = self.selected_quality_flag.get(); quality_flag = self.quality_options[quality_name]
        self.last_scene_name = scene_name; self.last_output_file = self._get_output_path(scene_name, quality_flag); self.video_saved_path = None
        self.manim_process = None # Limpa referência de processo anterior
        self.update_console(f"Iniciando renderização ({quality_name})... Por favor, aguarde.", "info")
        self.set_buttons_state("disabled", "Renderizando...", "Renderizando...") # Desabilita botões normais, habilita Forçar Parada
        thread = threading.Thread(target=self._run_manim, args=(code, scene_name, play, quality_flag), daemon=True); thread.start()

    def _get_output_path(self, scene_name, quality_flag):
        quality_folder_map = {"-ql": "480p15", "-qm": "720p30", "-qh": "1080p60", "-qk": "2160p60"}
        folder_name = quality_folder_map.get(quality_flag, "480p15")
        return os.path.join("media", "videos", "temp_animation", folder_name, f"{scene_name}.mp4")

    ### NOVA FUNÇÃO ###
    def _force_stop_manim(self):
        """ Tenta forçar a parada do processo Manim em execução. """
        if self.manim_process and self.manim_process.poll() is None: # Verifica se existe e está rodando
            try:
                self.manim_process.terminate() # Tenta terminar de forma "gentil"
                # Espera um pouco para ver se termina
                self.manim_process.wait(timeout=1)
                self.update_console("Processo Manim terminado pelo usuário.", "info")
            except subprocess.TimeoutExpired:
                # Se não terminou, força a parada (kill)
                try:
                    self.manim_process.kill()
                    self.update_console("Processo Manim forçado a parar (killed).", "info")
                except Exception as kill_e:
                    self.update_console(f"Erro ao forçar parada do processo: {kill_e}", "error")
            except Exception as e:
                self.update_console(f"Erro ao tentar terminar processo: {e}", "error")
            finally:
                self.manim_process = None
                # Reabilita os botões (exceto Forçar Parada)
                self.set_buttons_state("normal", "Renderizar", "Salvar Vídeo")
        else:
            self.update_console("Nenhum processo Manim em execução para parar.", "info")
            # Garante que o botão de parada seja desabilitado se não houver processo
            self.force_stop_btn.config(state="disabled")

    ### FUNÇÃO _run_manim MODIFICADA (Usa Popen) ###
    def _run_manim(self, code, scene_name, play=False, quality_flag="-ql"):
        temp_filename = "temp_animation.py"
        try:
            with open(temp_filename, "w", encoding="utf-8") as f: f.write(code)
        except Exception as e:
            self.after(0, self.update_console, f"Erro ao criar arquivo temporário: {e}", "error")
            self.after(0, self.set_buttons_state, "normal", "Renderizar", "Salvar Vídeo"); return

        command = ["manim", "--disable_caching", quality_flag, temp_filename, scene_name]
        if play: command.insert(2, "-p")

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        stdout_str = ""
        stderr_str = ""
        return_code = -1 # Código de retorno padrão

        try:
            # Usa Popen para iniciar o processo sem bloquear
            self.manim_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                 shell=True, startupinfo=startupinfo)

            # Espera o processo terminar e captura a saída
            # communicate() retorna (stdout_bytes, stderr_bytes)
            stdout_bytes, stderr_bytes = self.manim_process.communicate()
            return_code = self.manim_process.returncode

            # --- Decodificação Segura ---
            stdout_encoding = getattr(sys.stdout, 'encoding', None) or locale.getpreferredencoding() or 'utf-8'
            stderr_encoding = getattr(sys.stderr, 'encoding', None) or locale.getpreferredencoding() or 'utf-8'
            try: stdout_str = stdout_bytes.decode(stdout_encoding, errors='replace')
            except Exception as decode_e: stdout_str = f"[Erro ao decodificar stdout: {decode_e}]\n{stdout_bytes!r}"
            try: stderr_str = stderr_bytes.decode(stderr_encoding, errors='replace')
            except Exception as decode_e: stderr_str = f"[Erro ao decodificar stderr: {decode_e}]\n{stderr_bytes!r}"
            # --- Fim da Decodificação Segura ---

            # Verifica o código de retorno APÓS o processo ter terminado
            if return_code != 0:
                error_message = f"MANIM ERRO (Código: {return_code}):\n\n--- Saída de Erro (stderr) ---\n{stderr_str}\n\n--- Saída Padrão (stdout) ---\n{stdout_str}"
                self.after(0, self.update_console, error_message.strip(), "error"); return

            # --- Se chegou aqui, a execução do Manim foi OK ---
            output_file = self.last_output_file
            if not os.path.exists(output_file):
                error_msg = (f"Renderização concluída (Manim OK), mas não encontrou '{output_file}'\n\n"
                             f"--- stdout ---\n{stdout_str}\n\n--- stderr ---\n{stderr_str}")
                self.after(0, self.update_console, error_msg.strip(), "error"); return

            self.video_saved_path = output_file
            if not play: self.after(0, self.save_video)
            else:
                success_msg = f"Renderização concluída! Reproduzindo...\n\n--- stdout ---\n{stdout_str}"
                self.after(0, self.update_console, success_msg.strip(), "success")
                self.after(1000, self.clear_temp_media, output_file)

        except FileNotFoundError:
            error_msg = "Erro Crítico do App: Comando 'manim' não encontrado..."
            self.after(0, self.update_console, error_msg, "error")
        except Exception as e:
            import traceback
            tb_str = traceback.format_exc()
            error_msg = f"Erro Inesperado na execução do App:\n{type(e).__name__}: {e}\n\nTraceback do App:\n{tb_str}"
            self.after(0, self.update_console, error_msg, "error")
        finally:
            self.manim_process = None # Limpa a referência ao processo
            # Reabilita botões normais, desabilita Forçar Parada
            self.after(0, self.set_buttons_state, "normal", "Renderizar", "Salvar Vídeo")
            if os.path.exists(temp_filename):
                try: os.remove(temp_filename)
                except Exception: pass

    def clear_temp_media(self, source_path):
        try:
            temp_media_dir = os.path.abspath(os.path.join(source_path, "..", "..", ".."))
            if os.path.exists(temp_media_dir) and "temp_animation" in temp_media_dir: shutil.rmtree(temp_media_dir, ignore_errors=True)
        except Exception as e: print(f"Não foi possível limpar a pasta temp: {e}")

    def save_video(self):
        source_path = None; scene_name = "minha_animacao"
        if hasattr(self, 'video_saved_path') and self.video_saved_path and os.path.exists(self.video_saved_path):
             source_path = self.video_saved_path; scene_name = self.last_scene_name
        elif hasattr(self, 'last_output_file') and os.path.exists(self.last_output_file):
             source_path = self.last_output_file; scene_name = self.last_scene_name
        else: self.update_console("Nenhum vídeo renderizado encontrado...", "error"); return
        initial_filename = f"{scene_name}.mp4"
        save_path = filedialog.asksaveasfilename(defaultextension=".mp4", filetypes=[("MP4 Video", "*.mp4")], title="Salvar animação como...", initialfile=initial_filename)
        if save_path:
            try:
                shutil.copy(source_path, save_path)
                self.update_console(f"Animação salva com sucesso em: {save_path}", "success")
                self.clear_temp_media(source_path); self.video_saved_path = None
            except Exception as e: self.update_console(f"Erro ao salvar vídeo: {e}", "error")
        else: self.update_console("Salvamento de vídeo cancelado.", "info")

# FIM DA CLASSE ManimApp

if __name__ == "__main__":
    # Adiciona import locale aqui se ainda não estiver no topo
    import locale
    app = ManimApp()
    app.mainloop()