import os
import json
import tempfile
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from datetime import datetime
import ctypes
import re
import sys

META_FILENAME = ".metanotes.json"
CONFIG_FILE = "metadata.json"

# --- Auto Scrollbar ---
class AutoScrollbar(ttk.Scrollbar):
    """Scrollbar that automatically hides when not needed."""
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(lo, hi)

# --- Text Widget with Line Numbers ---
class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.text_widget = None
        self.font = "TkDefaultFont"

    def attach(self, text_widget):
        self.text_widget = text_widget
        
    def redraw(self, *args):
        self.delete("all")
        
        if not self.text_widget:
            return
            
        i = self.text_widget.index("@0,0")
        while True:
            dline = self.text_widget.dlineinfo(i)
            if dline is None:
                break
            y = dline[1]
            line_num = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=line_num, fill="grey", font=self.font)
            i = self.text_widget.index("%s+1line" % i)

class CustomText(ttk.Frame):
    def __init__(self, *args, **kwargs):
        ttk.Frame.__init__(self, *args, **kwargs)
        
        # Text widget - wrap mode will be set by the application
        self.text = tk.Text(
            self, 
            wrap='none',  # Default to no wrap, will be configured by app
            undo=True, 
            font=("Consolas", 11),
            selectbackground="#3d7aab",
            inactiveselectbackground="#3d7aab"
        )
        
        # Line numbers
        self.line_numbers = TextLineNumbers(self, width=40)
        self.line_numbers.attach(self.text)
        
        # Scrollbar
        self.v_scrollbar = AutoScrollbar(self, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.v_scrollbar.set)
        
        # Horizontal scrollbar for when wrap is disabled
        self.h_scrollbar = AutoScrollbar(self, orient="horizontal", command=self.text.xview)
        self.text.configure(xscrollcommand=self.h_scrollbar.set)
        
        # Layout
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.text.grid(row=0, column=1, sticky="nsew")
        self.v_scrollbar.grid(row=0, column=2, sticky="ns")
        self.h_scrollbar.grid(row=1, column=1, sticky="ew")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # Bind events
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Button-1>", self.on_key_release)
        self.text.bind("<MouseWheel>", self.on_key_release)
        
    def on_key_release(self, event=None):
        self.line_numbers.redraw()
        
    def get(self, *args, **kwargs):
        return self.text.get(*args, **kwargs)
        
    def insert(self, *args, **kwargs):
        result = self.text.insert(*args, **kwargs)
        self.on_key_release()
        return result
        
    def delete(self, *args, **kwargs):
        result = self.text.delete(*args, **kwargs)
        self.on_key_release()
        return result
        
    def index(self, *args, **kwargs):
        return self.text.index(*args, **kwargs)
        
    def bind(self, *args, **kwargs):
        return self.text.bind(*args, **kwargs)
        
    def edit_undo(self, *args, **kwargs):
        result = self.text.edit_undo(*args, **kwargs)
        self.on_key_release()
        return result
        
    def edit_redo(self, *args, **kwargs):
        result = self.text.edit_redo(*args, **kwargs)
        self.on_key_release()
        return result
        
    def edit_modified(self, *args, **kwargs):
        return self.text.edit_modified(*args, **kwargs)
        
    def edit_reset(self, *args, **kwargs):
        return self.text.edit_reset(*args, **kwargs)
        
    def config(self, *args, **kwargs):
        return self.text.config(*args, **kwargs)

# --- Utility functions ---
def atomic_write_json(path, data):
    dir_name = os.path.dirname(path)
    with tempfile.NamedTemporaryFile("w", dir=dir_name, delete=False, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name
    os.replace(temp_name, path)

def set_hidden(filepath, hidden=True):
    if os.name != 'nt':
        base = os.path.basename(filepath)
        dir_name = os.path.dirname(filepath)
        if hidden and not base.startswith('.'):
            os.rename(filepath, os.path.join(dir_name, '.' + base))
        elif not hidden and base.startswith('.'):
            os.rename(filepath, os.path.join(dir_name, base[1:]))
    else:
        FILE_ATTRIBUTE_HIDDEN = 0x02
        attrs = ctypes.windll.kernel32.GetFileAttributesW(str(filepath))
        if hidden:
            ctypes.windll.kernel32.SetFileAttributesW(str(filepath), attrs | FILE_ATTRIBUTE_HIDDEN)
        else:
            ctypes.windll.kernel32.SetFileAttributesW(str(filepath), attrs & ~FILE_ATTRIBUTE_HIDDEN)

def get_app_folder():
    # If we're in a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

# --- Application ---
class MetaNotesApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MetaNotes")
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Set window icon (if available)
        try:
            self.root.iconbitmap(default="metanotes.ico")
        except:
            pass

        # --- Variables ---
        self.current_folder = None
        self.notes = {}
        self.open_tabs = {}
        self.display_to_real_name = {}
        self.current_panel = "explorer"
        self.themes = ["superhero", "darkly", "solar", "cyborg", "vapor"]
        self.current_theme = "superhero"
        self.auto_save = True
        self.word_wrap = True
        self.font_size = 11
        self.font_family = "Consolas"
        self.search_history = []
        self.max_search_history = 10

        # --- Top frame (directory) ---
        self.top_frame = ttk.Frame(root, padding=10)
        self.top_frame.pack(side=TOP, fill=X)

        # Folder selection with modern look
        folder_frame = ttk.Frame(self.top_frame)
        folder_frame.pack(side=LEFT, fill=X, expand=True)
        
        ttk.Label(folder_frame, text="📁 Directory:", font=("Segoe UI", 10, "bold")).pack(side=LEFT, padx=(0,5))
        self.path_entry = ttk.Entry(folder_frame, width=60, font=("Segoe UI", 10))
        self.path_entry.pack(side=LEFT, fill=X, expand=True)
        self.path_entry.bind("<Return>", self.validate_path)
        self.path_entry.bind("<FocusOut>", self.cancel_path_edit)

        self.choose_folder_btn = ttk.Button(
            folder_frame, text="Browse", bootstyle="primary",
            command=self.choose_folder
        )
        self.choose_folder_btn.pack(side=LEFT, padx=5)
        
        # Quick actions
        quick_actions_frame = ttk.Frame(self.top_frame)
        quick_actions_frame.pack(side=RIGHT)
        
        self.save_all_btn = ttk.Button(
            quick_actions_frame, text="💾 Save All", bootstyle="info-outline",
            command=self.save_all_tabs, width=15
        )
        self.save_all_btn.pack(side=LEFT, padx=2)

        # --- Status Bar ---
        self.status_bar = ttk.Frame(root, height=22)
        self.status_bar.pack(side=BOTTOM, fill=X)
        self.status_bar.pack_propagate(False)
        
        self.status_label = ttk.Label(self.status_bar, text="Ready", font=("Segoe UI", 9))
        self.status_label.pack(side=LEFT, padx=10)
        
        self.word_count_label = ttk.Label(self.status_bar, text="Words: 0", font=("Segoe UI", 9))
        self.word_count_label.pack(side=RIGHT, padx=10)

        # --- Main PanedWindow ---
        style = ttk.Style()
        style.configure('Custom.TPanedwindow', sashrelief='flat', sashthickness=5)
        self.paned = ttk.PanedWindow(root, orient=HORIZONTAL, style='Custom.TPanedwindow')
        self.paned.pack(fill=BOTH, expand=True, padx=5, pady=5)

        # --- Left toolbar ---
        self.toolbar_frame = ttk.Frame(self.paned, width=60)
        self.paned.add(self.toolbar_frame, weight=0)
        
        # Navigation buttons with modern icons
        nav_buttons = [
            ("📁 Explorer", self.show_explorer, "File explorer"),
            ("🔍 Search", self.show_search, "Advanced search"),
            ("📊 Statistics", self.show_stats, "Directory statistics"),
            ("⚙️ Preferences", self.show_preferences, "Preferences")
        ]
        
        for text, command, _ in nav_buttons:
            btn = ttk.Button(
                self.toolbar_frame, 
                text=text, 
                command=command,
                width=15
            )
            btn.pack(fill=X, pady=2, padx=5)
        
        # Theme selector
        theme_frame = ttk.LabelFrame(self.toolbar_frame, text="Theme", padding=5)
        theme_frame.pack(fill=X, pady=10, padx=5)
        
        self.theme_var = tk.StringVar(value=self.current_theme)
        for theme in self.themes:
            rb = ttk.Radiobutton(
                theme_frame, 
                text=theme.capitalize(), 
                variable=self.theme_var, 
                value=theme,
                command=self.change_theme
            )
            rb.pack(anchor="w", pady=2)

        # --- Main frame for list/search ---
        self.main_frame = ttk.Frame(self.paned)
        self.paned.add(self.main_frame, weight=1)

        # --- Explorer panel ---
        self.list_frame = ttk.Frame(self.main_frame)
        self.list_frame.pack(fill=BOTH, expand=True)
        
        # File list with filter
        filter_frame = ttk.Frame(self.list_frame)
        filter_frame.pack(fill=X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=LEFT, padx=(0,5))
        self.file_filter = ttk.Entry(filter_frame)
        self.file_filter.pack(side=LEFT, fill=X, expand=True)
        self.file_filter.bind("<KeyRelease>", self.filter_file_list)
        
        # File list with scrollbars
        list_container = ttk.Frame(self.list_frame)
        list_container.pack(fill=BOTH, expand=True, padx=5, pady=(0,5))
        
        self.file_listbox = tk.Listbox(
            list_container, 
            width=35, 
            exportselection=0,
            font=("Segoe UI", 10),
            selectbackground="#3d7aab"
        )
        self.file_listbox.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = AutoScrollbar(list_container, orient="vertical", command=self.file_listbox.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.file_listbox.config(yscrollcommand=self.v_scrollbar.set)

        self.h_scrollbar = AutoScrollbar(list_container, orient="horizontal", command=self.file_listbox.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")
        self.file_listbox.config(xscrollcommand=self.h_scrollbar.set)

        list_container.rowconfigure(0, weight=1)
        list_container.columnconfigure(0, weight=1)
        self.file_listbox.bind("<Double-Button-1>", self.open_selected_file)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # --- Search panel ---
        self.search_frame = ttk.Frame(self.main_frame)
        
        # Search input with history
        search_input_frame = ttk.Frame(self.search_frame)
        search_input_frame.pack(fill=X, padx=5, pady=5)
        
        self.search_entry = ttk.Combobox(
            search_input_frame, 
            values=self.search_history,
            font=("Segoe UI", 10)
        )
        self.search_entry.pack(fill=X, side=LEFT, expand=True)
        self.search_entry.set("Search...")
        self.search_entry.config(foreground="grey")
        self.search_entry.bind("<FocusIn>", lambda e: self.clear_search_placeholder())
        self.search_entry.bind("<FocusOut>", lambda e: self.add_search_placeholder())
        self.search_entry.bind("<KeyRelease>", self.update_search_results)
        self.search_entry.bind("<<ComboboxSelected>>", self.update_search_results)
        
        self.search_btn = ttk.Button(
            search_input_frame, 
            text="🔍", 
            width=3,
            command=self.update_search_results
        )
        self.search_btn.pack(side=RIGHT, padx=(5,0))

        # --- Search options ---
        options_frame = ttk.LabelFrame(self.search_frame, text="Search Options", padding=5)
        options_frame.pack(fill=X, padx=5, pady=(0,5))

        self.match_case_var = tk.BooleanVar(value=False)
        self.match_whole_var = tk.BooleanVar(value=False)
        self.use_regex_var = tk.BooleanVar(value=False)

        self.match_case_cb = ttk.Checkbutton(
            options_frame, text="Match Case", 
            variable=self.match_case_var, 
            command=self.update_search_results
        )
        self.match_case_cb.pack(side=LEFT, padx=5)
        
        self.match_whole_cb = ttk.Checkbutton(
            options_frame, text="Whole Word", 
            variable=self.match_whole_var, 
            command=self.update_search_results
        )
        self.match_whole_cb.pack(side=LEFT, padx=5)
        
        self.use_regex_cb = ttk.Checkbutton(
            options_frame, text="Regular Expression", 
            variable=self.use_regex_var, 
            command=self.update_search_results
        )
        self.use_regex_cb.pack(side=LEFT, padx=5)

        # Alt shortcuts to toggle checkboxes
        self.root.bind_all("<Alt-c>", lambda e: self.toggle_checkbox(self.match_case_var))
        self.root.bind_all("<Alt-w>", lambda e: self.toggle_checkbox(self.match_whole_var))
        self.root.bind_all("<Alt-r>", lambda e: self.toggle_checkbox(self.use_regex_var))

        # Results list with counter
        results_frame = ttk.Frame(self.search_frame)
        results_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        self.results_count = ttk.Label(results_frame, text="0 results")
        self.results_count.pack(anchor="w", pady=(0,5))
        
        self.search_results = tk.Listbox(
            results_frame, 
            exportselection=0,
            font=("Segoe UI", 10),
            selectbackground="#3d7aab"
        )
        self.search_results.pack(fill=BOTH, expand=True)
        self.search_results.bind("<Double-Button-1>", self.open_selected_search_result)

        # --- Stats panel ---
        self.stats_frame = ttk.Frame(self.main_frame)
        
        stats_content = ttk.Frame(self.stats_frame)
        stats_content.pack(fill=BOTH, expand=True, padx=20, pady=20)
        
        self.stats_text = tk.Text(
            stats_content, 
            wrap='word', 
            font=("Segoe UI", 11),
            state='disabled',
            background=self.root.style.colors.bg,
            foreground=self.root.style.colors.fg,
            relief='flat'
        )
        self.stats_text.pack(fill=BOTH, expand=True)

        # --- Preferences panel ---
        self.prefs_frame = ttk.Frame(self.main_frame)
        
        prefs_content = ttk.Frame(self.prefs_frame, padding=20)
        prefs_content.pack(fill=BOTH, expand=True)
        
        # Auto-save
        self.auto_save_var = tk.BooleanVar(value=self.auto_save)
        auto_save_cb = ttk.Checkbutton(
            prefs_content, 
            text="Auto-save", 
            variable=self.auto_save_var,
            command=self.toggle_auto_save
        )
        auto_save_cb.pack(anchor="w", pady=5)
        
        # Word wrap
        self.word_wrap_var = tk.BooleanVar(value=self.word_wrap)
        word_wrap_cb = ttk.Checkbutton(
            prefs_content, 
            text="Word Wrap", 
            variable=self.word_wrap_var,
            command=self.toggle_word_wrap
        )
        word_wrap_cb.pack(anchor="w", pady=5)
        
        # Font size
        font_frame = ttk.Frame(prefs_content)
        font_frame.pack(fill=X, pady=10)
        
        ttk.Label(font_frame, text="Font Size:").pack(side=LEFT)
        self.font_size_var = tk.IntVar(value=self.font_size)
        font_size_spin = ttk.Spinbox(
            font_frame, 
            from_=8, 
            to=24, 
            width=5,
            textvariable=self.font_size_var,
            command=self.change_font_size
        )
        font_size_spin.pack(side=LEFT, padx=5)
        font_size_spin.bind("<Return>", lambda e: self.change_font_size())

        # --- Notebook (tabs) ---
        self.notebook_frame = ttk.Frame(self.paned)
        self.paned.add(self.notebook_frame, weight=4)
        
        # Notebook with close buttons
        self.notebook = ttk.Notebook(self.notebook_frame, bootstyle="secondary")
        self.notebook.pack(fill=BOTH, expand=True)
        self.notebook.bind("<ButtonPress-2>", self.on_middle_click)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        # --- Shortcuts ---
        self.root.bind_all("<Control-s>", self.ctrl_s)
        self.root.bind_all("<Control-S>", self.ctrl_s)
        self.root.bind_all("<Control-z>", self.ctrl_z)
        self.root.bind_all("<Control-y>", self.ctrl_y)
        self.root.bind_all("<Control-Shift-Z>", self.ctrl_y)
        self.root.bind_all("<Control-Shift-F>", lambda e: self.show_search())
        self.root.bind_all("<Control-w>", self.ctrl_w)
        self.root.bind_all("<F5>", lambda e: self.refresh_file_list())

        # --- Load config ---
        self.load_config()
        self.load_last_folder()
        self.apply_theme(self.current_theme)
        
        # Auto-save timer
        if self.auto_save:
            self.root.after(30000, self.auto_save_timer)  # Save every 30 seconds

    # --- Window closing handler ---
    def on_closing(self):
        """Handle window closing - ask to save each modified file individually"""
        modified_files = []
        
        # Find all modified files
        for filename, tab_data in self.open_tabs.items():
            if tab_data["modified"]:
                modified_files.append(filename)
        
        if not modified_files:
            self.root.destroy()
            return
        
        # Ask for each modified file individually
        for filename in modified_files:
            response = messagebox.askyesnocancel(
                "Save Changes?",
                f"The file '{filename}' has unsaved changes.\nDo you want to save it?",
                default=messagebox.YES
            )
            
            if response is None:  # Cancel
                return  # Don't close the window
            elif response:  # Yes
                self.save_tab_content(filename)
            # No - don't save and continue to next file
        
        self.root.destroy()

    # --- Placeholder Search ---
    def clear_search_placeholder(self):
        if self.search_entry.get() == "Search...":
            self.search_entry.delete(0, 'end')
            self.search_entry.config(foreground="white")

    def add_search_placeholder(self):
        if not self.search_entry.get():
            self.search_entry.set("Search...")
            self.search_entry.config(foreground="grey")

    # --- Toggle checkbox via Alt ---
    def toggle_checkbox(self, var):
        var.set(not var.get())
        self.update_search_results()

    # --- Auto-save ---
    def auto_save_timer(self):
        if self.auto_save:
            self.save_all_tabs(silent=True)
        self.root.after(30000, self.auto_save_timer)  # Repeat every 30 seconds

    def toggle_auto_save(self):
        """Enable or disable auto-save."""
        self.auto_save = self.auto_save_var.get()
        if self.auto_save:
            self.auto_save_timer()

    # --- Word wrap ---
    def toggle_word_wrap(self):
        self.word_wrap = self.word_wrap_var.get()
        wrap_mode = 'word' if self.word_wrap else 'none'
        for tab_data in self.open_tabs.values():
            text_widget = tab_data["text_widget"]
            text_widget.text.config(wrap=wrap_mode)
            # Show/hide horizontal scrollbar based on wrap mode
            if wrap_mode == 'none':
                text_widget.h_scrollbar.grid(row=1, column=1, sticky="ew")
            else:
                text_widget.h_scrollbar.grid_remove()

    # --- Font size ---
    def change_font_size(self, event=None):
        """Update font size for all open tabs and apply to new tabs."""
        self.font_size = self.font_size_var.get()
        font = (self.font_family, self.font_size)
        for tab_data in self.open_tabs.values():
            text_widget = tab_data["text_widget"]
            text_widget.text.config(font=font)
            # Update the line numbers canvas font too
            text_widget.line_numbers.font = font
            text_widget.line_numbers.redraw()
        
        self.save_config()  # Ensure new font size is saved

    # --- Config ---
    def load_config(self):
        """Load configuration from file and update app variables and widgets."""
        script_folder = get_app_folder()
        config_path = os.path.join(script_folder, CONFIG_FILE)
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    # Charger les valeurs avec des valeurs par défaut
                    self.current_theme = config.get("theme", "superhero")
                    self.auto_save = config.get("auto_save", True)
                    self.word_wrap = config.get("word_wrap", True)
                    self.font_size = config.get("font_size", 11)
                    self.font_family = config.get("font_family", "Consolas")
                    self.search_history = config.get("search_history", [])
                    
                    # Charger le dernier dossier si disponible
                    last_folder = config.get("last_folder")
                    if last_folder and os.path.isdir(last_folder):
                        self.current_folder = last_folder
                        
            except Exception as e:
                print(f"Config load error: {e}, using defaults")
                # Utiliser les valeurs par défaut en cas d'erreur
                self.current_theme = "superhero"
                self.auto_save = True
                self.word_wrap = True
                self.font_size = 11
                self.font_family = "Consolas"
                self.search_history = []
        
        # Mettre à jour les widgets Tkinter s'ils existent
        if hasattr(self, 'theme_var'):
            self.theme_var.set(self.current_theme)
        if hasattr(self, 'auto_save_var'):
            self.auto_save_var.set(self.auto_save)
        if hasattr(self, 'word_wrap_var'):
            self.word_wrap_var.set(self.word_wrap)
        if hasattr(self, 'font_size_var'):
            self.font_size_var.set(self.font_size)
        
        # Appliquer le thème chargé
        if hasattr(self, 'root'):
            self.apply_theme(self.current_theme)

    def save_config(self):
        script_folder = get_app_folder()
        config_path = os.path.join(script_folder, CONFIG_FILE)
        config = {
            "theme": self.current_theme, 
            "last_folder": self.current_folder,
            "auto_save": self.auto_save,
            "word_wrap": self.word_wrap,
            "font_size": self.font_size,
            "search_history": self.search_history[-self.max_search_history:]
        }
        atomic_write_json(config_path, config)

    def change_theme(self):
        self.current_theme = self.theme_var.get()
        self.apply_theme(self.current_theme)
        self.save_config()

    def apply_theme(self, theme):
        """Apply theme to the app and update widgets."""
        self.root.style.theme_use(theme)
        
        # Update stats panel colors
        if hasattr(self, 'stats_text'):
            self.stats_text.config(
                background=self.root.style.colors.bg,
                foreground=self.root.style.colors.fg
            )
        
        # Update notebook tabs background (optional, for modern look)
        for tab_data in self.open_tabs.values():
            tab_data["text_widget"].text.config(
                background=self.root.style.colors.bg,
                foreground=self.root.style.colors.fg,
                insertbackground=self.root.style.colors.fg
            )


    # --- Panels switch ---
    def show_explorer(self):
        self.hide_all_panels()
        self.list_frame.pack(fill=BOTH, expand=True)
        self.current_panel = "explorer"
        self.status_label.config(text="Mode: File Explorer")

    def show_search(self):
        self.hide_all_panels()
        self.search_frame.pack(fill=BOTH, expand=True)
        self.current_panel = "search"
        self.search_entry.focus_set()
        self.add_search_placeholder()
        self.update_search_results()
        self.status_label.config(text="Mode: Search")

    def show_stats(self):
        self.hide_all_panels()
        self.stats_frame.pack(fill=BOTH, expand=True)
        self.current_panel = "stats"
        self.update_stats()
        self.status_label.config(text="Mode: Statistics")

    def show_preferences(self):
        self.hide_all_panels()
        self.prefs_frame.pack(fill=BOTH, expand=True)
        self.current_panel = "preferences"
        self.status_label.config(text="Mode: Preferences")

    def hide_all_panels(self):
        for panel in [self.list_frame, self.search_frame, self.stats_frame, self.prefs_frame]:
            panel.pack_forget()

    # --- File list filter ---
    def filter_file_list(self, event=None):
        filter_text = self.file_filter.get().lower()
        self.file_listbox.delete(0, 'end')
        
        for entry in os.listdir(self.current_folder):
            full_path = os.path.join(self.current_folder, entry)
            if entry == META_FILENAME:
                continue
                
            if filter_text and filter_text not in entry.lower():
                continue
                
            display_name = f"📁 {entry}" if os.path.isdir(full_path) else entry
            self.display_to_real_name[display_name] = entry
            self.file_listbox.insert('end', display_name)

    # --- Search Results ---
    def update_search_results(self, event=None):
        query = self.search_entry.get().strip()
        
        # Gérer le placeholder et les recherches vides
        if not query or query.lower() == "search...":
            self.search_results.delete(0, 'end')
            self.results_count.config(text="0 results")
            return

        # Mettre à jour l'historique de recherche
        if query not in self.search_history and query != "Search...":
            self.search_history.append(query)
            if len(self.search_history) > self.max_search_history:
                self.search_history.pop(0)
            self.search_entry.config(values=self.search_history)

        # Préparer les résultats
        self.search_results.delete(0, 'end')
        results_count = 0

        for name, content in self.notes.items():
            if name == "_meta":
                continue

            haystack = content
            needle = query

            # Match Case
            if not self.match_case_var.get():
                haystack = haystack.lower()
                needle = needle.lower()

            # Regex
            if self.use_regex_var.get():
                try:
                    if re.search(needle, haystack):
                        self.search_results.insert('end', name)
                        results_count += 1
                    continue
                except re.error as e:
                    # En cas d'erreur regex, fallback sur la recherche simple
                    if needle in haystack:
                        self.search_results.insert('end', name)
                        results_count += 1
                    continue

            # Whole Word
            if self.match_whole_var.get():
                try:
                    pattern = r'\b{}\b'.format(re.escape(needle))
                    if re.search(pattern, haystack):
                        self.search_results.insert('end', name)
                        results_count += 1
                except re.error:
                    # Fallback sur la recherche simple en cas d'erreur
                    if needle in haystack:
                        self.search_results.insert('end', name)
                        results_count += 1
            else:
                # Simple substring
                if needle in haystack:
                    self.search_results.insert('end', name)
                    results_count += 1

        self.results_count.config(text=f"{results_count} result(s)")
        
        # Mettre à jour le statut
        if hasattr(self, 'status_label') and self.current_panel == "search":
            self.status_label.config(text=f"Search: {results_count} results for '{query}'")

    def open_selected_search_result(self, event=None):
        selection = self.search_results.curselection()
        if not selection:
            return
        index = selection[0]
        filename = self.search_results.get(index)
        self.select_and_open_file(filename)

    # --- Directory ---
    def load_last_folder(self):
        script_folder = get_app_folder()
        config_path = os.path.join(script_folder, CONFIG_FILE)
        folder = script_folder
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    folder = json.load(f).get("last_folder", script_folder)
                    if not os.path.isdir(folder):
                        folder = script_folder
            except: folder = script_folder
        self.set_folder(folder)

    def save_last_folder(self):
        self.save_config()

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.current_folder)
        if folder:
            self.set_folder(folder)

    def set_folder(self, folder):
        if not os.path.isdir(folder):
            messagebox.showerror("Error", f"The directory '{folder}' is invalid.")
            return
        
        # Close all opened tabs
        for tab_id in reversed(range(len(self.notebook.tabs()))):
            if not self.close_tab(tab_id):  # If Cancel
                return  # Do no change the folder
        
        self.current_folder = folder
        self.path_entry.delete(0, 'end')
        self.path_entry.insert(0, self.current_folder)
        self.load_notes()
        self.populate_file_list()
        self.save_last_folder()
        self.status_label.config(text=f"Directory loaded: {folder}")


    def validate_path(self, event=None):
        new_path = self.path_entry.get()
        if os.path.isdir(new_path):
            self.set_folder(new_path)
        else:
            messagebox.showerror("Error", f"The directory '{new_path}' is invalid.")
            self.cancel_path_edit()

    def cancel_path_edit(self, event=None):
        self.path_entry.delete(0, 'end')
        self.path_entry.insert(0, self.current_folder if self.current_folder else os.path.dirname(os.path.abspath(__file__)))

    # --- Files and Notes ---
    def populate_file_list(self):
        self.file_listbox.delete(0, 'end')
        self.display_to_real_name = {}
        for entry in os.listdir(self.current_folder):
            full_path = os.path.join(self.current_folder, entry)
            if entry == META_FILENAME:
                continue
            display_name = f"📁 {entry}" if os.path.isdir(full_path) else entry
            self.display_to_real_name[display_name] = entry
            self.file_listbox.insert('end', display_name)

    def on_file_select(self, event=None):
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            display_name = self.file_listbox.get(index)
            filename = self.display_to_real_name.get(display_name, display_name)
            full_path = os.path.join(self.current_folder, filename)
            
            if os.path.isfile(full_path):
                # Show file info in status bar
                file_size = os.path.getsize(full_path)
                modified_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                self.status_label.config(text=f"{filename} - {file_size} bytes - Modified: {modified_time.strftime('%m/%d/%Y %H:%M')}")

    def load_notes(self):
        self.notes = {}
        meta_path = os.path.join(self.current_folder, META_FILENAME)
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.notes = json.load(f)
            except:
                messagebox.showerror("Error", "Unable to read the notes file.")
        else:
            self.notes = {"_meta": {"created": datetime.now().isoformat()}}
            self.save_notes_all()

    def save_notes_all(self):
        meta_path = os.path.join(self.current_folder, META_FILENAME)
        for filename, tab_data in self.open_tabs.items():
            text_widget = tab_data["text_widget"]
            self.notes[filename] = text_widget.get("1.0", 'end').strip()
        atomic_write_json(meta_path, self.notes)
        set_hidden(meta_path, True)
        self.save_last_folder()

    # --- Save all ---
    def save_all_tabs(self, silent=False):
        for filename in list(self.open_tabs.keys()):
            self.save_tab_content(filename)
        if not silent:
            self.status_label.config(text="All notes saved")
            messagebox.showinfo("Save", "All notes have been saved.")

    # --- Refresh list ---
    def refresh_file_list(self):
        self.populate_file_list()
        self.status_label.config(text="File list refreshed")

    # --- Statistics ---
    def update_stats(self):
        self.stats_text.config(state='normal')
        self.stats_text.delete('1.0', 'end')
        
        total_files = len([f for f in os.listdir(self.current_folder) if f != META_FILENAME])
        total_notes = len(self.notes) - 1  # Exclude _meta
        
        # Calculate word counts
        total_words = 0
        note_words = {}
        
        for name, content in self.notes.items():
            if name == "_meta":
                continue
            words = len(content.split())
            note_words[name] = words
            total_words += words
            
        # Display stats
        stats_text = f"""📊 DIRECTORY STATISTICS
==========================

Directory: {self.current_folder}
Files: {total_files}
Notes: {total_notes}
Total words: {total_words}

NOTES BY SIZE:
-----------------
"""
        # Sort notes by word count
        sorted_notes = sorted(note_words.items(), key=lambda x: x[1], reverse=True)
        
        for name, words in sorted_notes[:10]:  # Top 10
            stats_text += f"{name}: {words} words\n"
            
        if len(sorted_notes) > 10:
            stats_text += f"... and {len(sorted_notes) - 10} other notes\n"
            
        self.stats_text.insert('1.0', stats_text)
        self.stats_text.config(state='disabled')

    # --- Tabs ---
    def open_selected_file(self, event=None):
        selection = self.file_listbox.curselection()
        if not selection: 
            return
        index = selection[0]
        display_name = self.file_listbox.get(index)
        filename = self.display_to_real_name.get(display_name, display_name)
        self.select_and_open_file(filename)

    def select_and_open_file(self, filename):
        if filename in self.open_tabs:
            tab_frame = self.open_tabs[filename]["frame"]
            self.notebook.select(self.notebook.index(tab_frame))
        else:
            tab_frame = ttk.Frame(self.notebook)
            
            # Create custom text widget with line numbers
            text_widget = CustomText(tab_frame)
            text_widget.pack(fill=BOTH, expand=True, padx=5, pady=5)
            
            # Apply current font settings to the new tab
            font = (self.font_family, self.font_size)
            text_widget.text.config(font=font)
            text_widget.line_numbers.font = font
            
            # Apply current word wrap setting to the new tab
            wrap_mode = 'word' if self.word_wrap else 'none'
            text_widget.text.config(wrap=wrap_mode)
            
            # Show/hide horizontal scrollbar based on wrap mode
            if wrap_mode == 'none':
                text_widget.h_scrollbar.grid(row=1, column=1, sticky="ew")
            else:
                text_widget.h_scrollbar.grid_remove()
            
            note_content = self.notes.get(filename, "")
            text_widget.insert('end', note_content)
            text_widget.edit_reset()
            
            self.open_tabs[filename] = {
                "frame": tab_frame,
                "text_widget": text_widget,
                "modified": False,
                "original_content": note_content
            }
            
            text_widget.bind("<<Modified>>", lambda e, f=filename: self.on_text_modified(f))
            self.notebook.add(tab_frame, text=filename)
            self.notebook.select(self.notebook.index(tab_frame))
            
            # Update word count
            self.update_word_count(filename)

    def on_text_modified(self, filename):
        tab_data = self.open_tabs.get(filename)
        if tab_data:
            text_widget = tab_data["text_widget"]
            current_content = text_widget.get("1.0", 'end').strip()
            if current_content != tab_data["original_content"] and not tab_data["modified"]:
                tab_data["modified"] = True
                self.update_tab_title(filename)
            text_widget.edit_modified(False)
            
            # Update word count
            self.update_word_count(filename)

    def update_tab_title(self, filename):
        tab_data = self.open_tabs.get(filename)
        if tab_data:
            tab_frame = tab_data["frame"]
            tab_id = self.notebook.index(tab_frame)
            title = filename + (" *" if tab_data["modified"] else "")
            self.notebook.tab(tab_id, text=title)

    def on_tab_changed(self, event):
        # Update word count for current tab
        current_tab = self.notebook.select()
        for filename, tab_data in self.open_tabs.items():
            if str(tab_data["frame"]) == current_tab:
                self.update_word_count(filename)
                break

    def update_word_count(self, filename):
        tab_data = self.open_tabs.get(filename)
        if tab_data:
            content = tab_data["text_widget"].get("1.0", 'end').strip()
            words = len(content.split()) if content else 0
            chars = len(content)
            self.word_count_label.config(text=f"Words: {words} | Characters: {chars}")

    def on_middle_click(self, event):
        try:
            tab_id = self.notebook.index(f"@{event.x},{event.y}")
            if tab_id >= 0:
                self.close_tab(tab_id)
        except: pass

    def close_tab(self, tab_id):
        tab_frame = self.notebook.nametowidget(self.notebook.tabs()[tab_id])
        filename = None
        for fname, tab_data in self.open_tabs.items():
            if tab_data["frame"] == tab_frame:
                filename = fname
                break
        if filename:
            if self.open_tabs[filename]["modified"]:
                response = messagebox.askyesnocancel(
                    "Close Tab",
                    f"The file '{filename}' has unsaved changes. Save?"
                )
                if response is None:
                    return False  # User has canceled
                elif response:
                    self.save_tab_content(filename)
            self.notebook.forget(tab_id)
            del self.open_tabs[filename]
            # Update word count for new current tab
            current_tab = self.notebook.select()
            if current_tab:
                for fname, tab_data in self.open_tabs.items():
                    if str(tab_data["frame"]) == current_tab:
                        self.update_word_count(fname)
                        break
            else:
                self.word_count_label.config(text="Words: 0 | Characters: 0")
        return True  # Tab successfully closed


    def save_tab_content(self, filename):
        tab_data = self.open_tabs.get(filename)
        if tab_data:
            text_widget = tab_data["text_widget"]
            self.notes[filename] = text_widget.get("1.0", 'end').strip()
            tab_data["original_content"] = self.notes[filename]
            tab_data["modified"] = False
            self.update_tab_title(filename)
            self.save_notes_all()
            self.status_label.config(text=f"Note saved: {filename}")

    # --- Shortcuts ---
    def ctrl_s(self, event=None):
        current_tab = self.notebook.select()
        for filename, tab_data in self.open_tabs.items():
            if str(tab_data["frame"]) == current_tab:
                self.save_tab_content(filename)
                return "break"  # Prevent default behavior

    def ctrl_z(self, event=None):
        current_tab = self.notebook.select()
        for filename, tab_data in self.open_tabs.items():
            if str(tab_data["frame"]) == current_tab:
                try: 
                    tab_data["text_widget"].edit_undo()
                    tab_data["modified"] = tab_data["text_widget"].get("1.0", 'end').strip() != tab_data["original_content"]
                    self.update_tab_title(filename)
                    self.update_word_count(filename)
                except: pass
                return "break"

    def ctrl_y(self, event=None):
        current_tab = self.notebook.select()
        for filename, tab_data in self.open_tabs.items():
            if str(tab_data["frame"]) == current_tab:
                try: 
                    tab_data["text_widget"].edit_redo()
                    tab_data["modified"] = tab_data["text_widget"].get("1.0", 'end').strip() != tab_data["original_content"]
                    self.update_tab_title(filename)
                    self.update_word_count(filename)
                except: pass
                return "break"

    def ctrl_w(self, event=None):
        current_tab = self.notebook.select()
        if current_tab:
            tab_id = self.notebook.index(current_tab)
            self.close_tab(tab_id)
            return "break"

if __name__ == "__main__":
    root = ttk.Window(title="MetaNotes", themename="superhero")
    app = MetaNotesApp(root)
    root.geometry("1200x700")
    root.minsize(800, 500)
    root.mainloop()