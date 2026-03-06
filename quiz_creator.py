import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import time
from PIL import Image, ImageTk, ImageGrab

# Optional drag-and-drop support via tkinterdnd2 (pip install tkinterdnd2)
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

_BaseClass = TkinterDnD.Tk if _DND_AVAILABLE else tk.Tk

# Always resolve paths relative to the script's own directory so the app
# works regardless of which directory it is launched from.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_IMAGES_DIR = os.path.join(_SCRIPT_DIR, "images")

class QuizCreator(_BaseClass):
    def __init__(self):
        super().__init__()
        self.title("Quiz Creator")
        self.geometry("900x770")
        
        # Configure style for better contrast
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0', foreground='#000000')
        style.configure('TLabelframe', background='#e8e8e8', foreground='#000000')
        style.configure('TLabelframe.Label', background='#e8e8e8', foreground='#000000', font=('Arial', 10, 'bold'))
        
        # Configure canvas background
        self.configure(bg='#f0f0f0')
        
        # Data structure
        self.quiz_data = {
            "display_time": 5,
            "wait_before_next": 3,
            "questions": []
        }
        
        self.current_question = {
            "question": "",
            "question_image": "",
            "answers": [],
            "correct_answer_index": 0
        }
        
        self.current_answers = []  # List of {text: "", image: ""}
        self._editing_index = None       # index of question being edited, or None
        self._editing_answer_index = None  # index of answer being edited, or None
        self._loaded_filepath = None     # absolute path of the last loaded/saved file
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title = ttk.Label(self, text="Quiz Creator", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Create notebook (tab container)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create tabs
        settings_tab = ttk.Frame(self.notebook, padding="10")
        question_tab = ttk.Frame(self.notebook, padding="10")
        questions_list_tab = ttk.Frame(self.notebook, padding="10")
        file_tab = ttk.Frame(self.notebook, padding="10")
        
        self.notebook.add(settings_tab, text="Quiz Settings")
        self.notebook.add(question_tab, text="Create Question")
        self.notebook.add(questions_list_tab, text="Questions in Quiz")
        self.notebook.add(file_tab, text="File Operations")
        
        # === TAB 1: Quiz Settings ===
        settings_frame = ttk.LabelFrame(settings_tab, text="Global Settings", padding="10")
        settings_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Display Time (seconds):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.display_time_var = tk.StringVar(value="5")
        ttk.Entry(settings_frame, textvariable=self.display_time_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="Wait Before Next (seconds):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.wait_time_var = tk.StringVar(value="3")
        ttk.Entry(settings_frame, textvariable=self.wait_time_var, width=10).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # === TAB 2: Create Question ===
        question_frame = ttk.LabelFrame(question_tab, text="Question", padding="10")
        question_frame.pack(fill="both", expand=False, padx=5, pady=5)
        
        ttk.Label(question_frame, text="Question Text:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.question_text = tk.Text(question_frame, height=3, width=60)
        self.question_text.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(question_frame, text="Browse…", command=self.add_question_image).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Button(question_frame, text="📋 Paste", command=self._paste_question_image).grid(row=2, column=1, sticky=tk.W, padx=2, pady=5)

        self.question_image_label = ttk.Label(question_frame, text="No image  (drop file here or use Browse/Paste)",
                                              relief="groove", padding=4, width=45)
        self.question_image_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        # Answers Section (same tab)
        answers_frame = ttk.LabelFrame(question_tab, text="Answers", padding="10")
        answers_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Answer entry
        ttk.Label(answers_frame, text="Answer Text:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.answer_text_var = tk.StringVar()
        ttk.Entry(answers_frame, textvariable=self.answer_text_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(answers_frame, text="Browse…", command=self.add_answer_image).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Button(answers_frame, text="📋 Paste", command=self._paste_answer_image).grid(row=1, column=1, sticky=tk.W, padx=2, pady=5)

        self.answer_image_label = ttk.Label(answers_frame, text="No image  (drop file here or use Browse/Paste)",
                                            relief="groove", padding=4, width=45)
        self.answer_image_label.grid(row=2, column=0, columnspan=3, sticky=tk.W, padx=5, pady=2)
        
        self.add_answer_btn = ttk.Button(answers_frame, text="Add Answer", command=self.add_answer)
        self.add_answer_btn.grid(row=3, column=0, columnspan=2, pady=10)
        
        # hint
        ttk.Label(answers_frame, text="Double-click an answer to edit it",
                  foreground="gray").grid(row=3, column=2, sticky=tk.W, padx=8)
        
        # Answers list
        ttk.Label(answers_frame, text="Current Answers:").grid(row=4, column=0, sticky=tk.W, padx=5)
        
        # Frame for answers list with scrollbar
        list_frame = ttk.Frame(answers_frame)
        list_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.answers_listbox = tk.Listbox(list_frame, height=6, width=50, yscrollcommand=scrollbar.set)
        self.answers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.answers_listbox.yview)
        self.answers_listbox.bind("<Double-Button-1>", self._on_answer_double_click)
        
        # Correct answer selection
        ttk.Label(answers_frame, text="Correct Answer Index (0-based):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.correct_index_var = tk.StringVar(value="0")
        ttk.Entry(answers_frame, textvariable=self.correct_index_var, width=10).grid(row=6, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(answers_frame, text="Remove Selected Answer", command=self.remove_answer).grid(row=7, column=0, columnspan=2, pady=5)
        
        # Question Management buttons (same tab)
        management_frame = ttk.Frame(question_tab)
        management_frame.pack(pady=10)
        
        self.add_question_btn = ttk.Button(management_frame, text="Add Question to Quiz", command=self.add_question_to_quiz)
        self.add_question_btn.pack(side=tk.LEFT, padx=5)
        ttk.Button(management_frame, text="Clear Current Question", command=self.clear_current_question).pack(side=tk.LEFT, padx=5)
        
        # === TAB 3: Questions List ===
        questions_frame = ttk.LabelFrame(questions_list_tab, text="All Questions", padding="10")
        questions_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        list_frame2 = ttk.Frame(questions_frame)
        list_frame2.pack(fill=tk.BOTH, expand=True)
        
        scrollbar2 = ttk.Scrollbar(list_frame2)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.questions_listbox = tk.Listbox(list_frame2, height=6, width=50, yscrollcommand=scrollbar2.set)
        self.questions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar2.config(command=self.questions_listbox.yview)
        self.questions_listbox.bind("<Double-Button-1>", self._on_question_double_click)
        
        ttk.Button(questions_frame, text="Remove Selected Question", command=self.remove_question).pack(pady=5)
        ttk.Label(questions_frame, text="Double-click a question to edit it",
                  foreground="gray").pack()
        
        # === TAB 4: File Operations ===
        file_frame = ttk.LabelFrame(file_tab, text="File Management", padding="20")
        file_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self._loaded_file_var = tk.StringVar(value="(no file loaded)")

        ttk.Button(file_frame, text="Load Quiz", command=self.load_quiz, width=20).grid(row=0, column=0, pady=10, padx=5, sticky=tk.W)
        ttk.Label(file_frame, textvariable=self._loaded_file_var, foreground="#336699").grid(row=0, column=1, padx=10, sticky=tk.W)
        ttk.Button(file_frame, text="Save Quiz", command=self.save_quiz, width=20).grid(row=1, column=0, pady=10, padx=5, sticky=tk.W)
        ttk.Button(file_frame, text="New Quiz", command=self.new_quiz, width=20).grid(row=2, column=0, pady=10, padx=5, sticky=tk.W)

        ttk.Label(file_frame, text="Use these buttons to load, save, or create a new quiz.",
                 foreground="gray").grid(row=3, column=0, columnspan=2, pady=20, sticky=tk.W)
        
        # Store temporary image paths
        self.temp_question_image = ""
        self.temp_answer_image = ""

        # Register drag-and-drop drop targets (requires tkinterdnd2)
        if _DND_AVAILABLE:
            self.question_image_label.drop_target_register(DND_FILES)
            self.question_image_label.dnd_bind("<<Drop>>", self._on_drop_question_image)
            self.answer_image_label.drop_target_register(DND_FILES)
            self.answer_image_label.dnd_bind("<<Drop>>", self._on_drop_answer_image)
        else:
            # Grey out the label hint if DnD is unavailable
            self.question_image_label.config(text="No image  (use Browse or Paste — install tkinterdnd2 for drag-and-drop)")
            self.answer_image_label.config(text="No image  (use Browse or Paste — install tkinterdnd2 for drag-and-drop)")
        
    # ── Image helpers ──────────────────────────────────────────────────────────

    def _save_image_to_disk(self, pil_image: Image.Image, prefix: str = "img") -> str:
        """Save a PIL Image to <script_dir>/images/ with a timestamp name.
        Returns a path relative to the script directory."""
        os.makedirs(_IMAGES_DIR, exist_ok=True)
        abs_path = os.path.join(_IMAGES_DIR, f"{prefix}_{int(time.time() * 1000)}.png")
        pil_image.save(abs_path)
        return os.path.relpath(abs_path, start=_SCRIPT_DIR)

    def _set_question_image(self, path: str) -> None:
        self.temp_question_image = path
        self.question_image_label.config(text=f"✅ {os.path.basename(path)}")

    def _set_answer_image(self, path: str) -> None:
        self.temp_answer_image = path
        self.answer_image_label.config(text=f"✅ {os.path.basename(path)}")

    # ── Browse (file dialog) ───────────────────────────────────────────────────

    def add_question_image(self):
        """Browse and select question image."""
        filename = filedialog.askopenfilename(
            title="Select Question Image",
            initialdir=_IMAGES_DIR,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if filename:
            try:
                path = os.path.relpath(filename, start=_SCRIPT_DIR)
            except ValueError:
                path = filename  # different drive — keep absolute
            self._set_question_image(path)

    def add_answer_image(self):
        """Browse and select answer image."""
        filename = filedialog.askopenfilename(
            title="Select Answer Image",
            initialdir=_IMAGES_DIR,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if filename:
            try:
                path = os.path.relpath(filename, start=_SCRIPT_DIR)
            except ValueError:
                path = filename  # different drive — keep absolute
            self._set_answer_image(path)

    # ── Drag-and-drop handlers ─────────────────────────────────────────────────

    def _on_drop_question_image(self, event) -> None:
        """Handle a file dropped onto the question image label."""
        path = event.data.strip().strip("{}")  # Windows wraps space-containing paths in {}
        if os.path.isfile(path):
            try:
                path = os.path.relpath(path, start=_SCRIPT_DIR)
            except ValueError:
                pass  # different drive — keep absolute
            self._set_question_image(path)
        else:
            messagebox.showwarning("Drop", f"Could not find file:\n{path}")

    def _on_drop_answer_image(self, event) -> None:
        """Handle a file dropped onto the answer image label."""
        path = event.data.strip().strip("{}") 
        if os.path.isfile(path):
            try:
                path = os.path.relpath(path, start=_SCRIPT_DIR)
            except ValueError:
                pass  # different drive — keep absolute

    def _paste_question_image(self) -> None:
        """Read an image from the Windows clipboard and assign it to the question slot."""
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            path = self._save_image_to_disk(img, "question")
            self._set_question_image(path)
        else:
            messagebox.showwarning("Paste", "No image found on the clipboard.\n"
                                            "Copy an image first (e.g. Print Screen, "
                                            "right-click → Copy Image).")

    def _paste_answer_image(self) -> None:
        """Read an image from the Windows clipboard and assign it to the answer slot."""
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            path = self._save_image_to_disk(img, "answer")
            self._set_answer_image(path)
        else:
            messagebox.showwarning("Paste", "No image found on the clipboard.\n"
                                            "Copy an image first (e.g. Print Screen, "
                                            "right-click → Copy Image).")
    
    def _on_answer_double_click(self, event) -> None:
        """Load a double-clicked answer back into the answer entry fields for editing."""
        selection = self.answers_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        answer = self.current_answers[index]
        self.answer_text_var.set(answer.get("text", ""))
        self.temp_answer_image = answer.get("image", "")
        if self.temp_answer_image:
            self.answer_image_label.config(text=f"\u2705 {os.path.basename(self.temp_answer_image)}")
        else:
            self.answer_image_label.config(text="No image  (drop file here or use Browse/Paste)")
        self._editing_answer_index = index
        self.add_answer_btn.config(text="\U0001f4be  Update Answer")

    def add_answer(self):
        """Add a new answer, or update an existing one if in answer-edit mode."""
        text = self.answer_text_var.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter answer text")
            return

        answer = {"text": text}
        if self.temp_answer_image:
            answer["image"] = self.temp_answer_image

        if self._editing_answer_index is not None:
            # Replace the existing answer in-place
            self.current_answers[self._editing_answer_index] = answer
            self._editing_answer_index = None
            self.add_answer_btn.config(text="Add Answer")
        else:
            self.current_answers.append(answer)

        self.refresh_answers_list()

        # Clear answer inputs
        self.answer_text_var.set("")
        self.temp_answer_image = ""
        self.answer_image_label.config(text="No image  (drop file here or use Browse/Paste)")
    
    def remove_answer(self):
        """Remove selected answer"""
        selection = self.answers_listbox.curselection()
        if selection:
            index = selection[0]
            self.current_answers.pop(index)
            self.answers_listbox.delete(index)
            # Update indices in listbox
            self.refresh_answers_list()
    
    def refresh_answers_list(self):
        """Refresh the answers listbox"""
        self.answers_listbox.delete(0, tk.END)
        for i, answer in enumerate(self.current_answers):
            display_text = f"{i}: {answer['text']}"
            if answer.get('image'):
                display_text += f" [Image: {os.path.basename(answer['image'])}]"
            self.answers_listbox.insert(tk.END, display_text)
    
    def _on_question_double_click(self, event) -> None:
        """Load the double-clicked question into the Create Question tab for editing."""
        selection = self.questions_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        q = self.quiz_data["questions"][index]

        # Populate question text
        self.question_text.delete("1.0", tk.END)
        self.question_text.insert(tk.END, q.get("question", ""))

        # Populate question image
        self.temp_question_image = q.get("question_image", "")
        if self.temp_question_image:
            self.question_image_label.config(text=f"\u2705 {os.path.basename(self.temp_question_image)}")
        else:
            self.question_image_label.config(text="No image  (drop file here or use Browse/Paste)")

        # Populate answers
        self.current_answers = [dict(a) for a in q.get("answers", [])]
        self.refresh_answers_list()

        # Populate correct answer index
        self.correct_index_var.set(str(q.get("correct_answer_index", 0)))

        # Remember which question we are editing
        self._editing_index = index
        self.add_question_btn.config(text="\U0001f4be  Save Changes")

        # Switch to Create Question tab (index 1)
        self.notebook.select(1)

    def add_question_to_quiz(self):
        """Add a new question, or save edits back to an existing one."""
        question_text = self.question_text.get("1.0", tk.END).strip()

        if not question_text:
            messagebox.showwarning("Warning", "Please enter question text")
            return

        if len(self.current_answers) < 2:
            messagebox.showwarning("Warning", "Please add at least 2 answers")
            return

        try:
            correct_index = int(self.correct_index_var.get())
            if correct_index < 0 or correct_index >= len(self.current_answers):
                messagebox.showwarning("Warning", f"Correct answer index must be between 0 and {len(self.current_answers)-1}")
                return
        except ValueError:
            messagebox.showwarning("Warning", "Correct answer index must be a number")
            return

        question = {
            "question": question_text,
            "answers": self.current_answers.copy(),
            "correct_answer_index": correct_index,
            "question_image": self.temp_question_image,
        }

        if self._editing_index is not None:
            # Overwrite the existing question in-place
            self.quiz_data["questions"][self._editing_index] = question
            self.refresh_questions_list()
            messagebox.showinfo("Saved", f"Question {self._editing_index + 1} updated.")
        else:
            # Append as a new question
            self.quiz_data["questions"].append(question)
            display_text = f"Q{len(self.quiz_data['questions'])}: {question_text[:50]}"
            if len(question_text) > 50:
                display_text += "..."
            self.questions_listbox.insert(tk.END, display_text)
            messagebox.showinfo("Success", "Question added to quiz!")

        self.clear_current_question()
    
    def clear_current_question(self):
        """Clear current question inputs and exit edit mode."""
        self.question_text.delete("1.0", tk.END)
        self.temp_question_image = ""
        _hint = "No image  (drop file here or use Browse/Paste)"
        self.question_image_label.config(text=_hint)
        self.current_answers = []
        self.answers_listbox.delete(0, tk.END)
        self.answer_text_var.set("")
        self.temp_answer_image = ""
        self.answer_image_label.config(text=_hint)
        self.correct_index_var.set("0")
        self._editing_index = None
        self._editing_answer_index = None
        self.add_question_btn.config(text="Add Question to Quiz")
        self.add_answer_btn.config(text="Add Answer")
    
    def remove_question(self):
        """Remove selected question from quiz"""
        selection = self.questions_listbox.curselection()
        if selection:
            index = selection[0]
            if messagebox.askyesno("Confirm", "Remove this question from the quiz?"):
                self.quiz_data["questions"].pop(index)
                self.questions_listbox.delete(index)
                # Refresh list with updated indices
                self.refresh_questions_list()
    
    def refresh_questions_list(self):
        """Refresh the questions listbox"""
        self.questions_listbox.delete(0, tk.END)
        for i, question in enumerate(self.quiz_data["questions"]):
            display_text = f"Q{i+1}: {question['question'][:50]}"
            if len(question['question']) > 50:
                display_text += "..."
            self.questions_listbox.insert(tk.END, display_text)
    
    def save_quiz(self):
        """Save quiz to JSON file, pre-filling the dialog with the originally loaded filename."""
        if not self.quiz_data["questions"]:
            messagebox.showwarning("Warning", "No questions to save")
            return

        # Update timing values
        try:
            self.quiz_data["display_time"] = int(self.display_time_var.get())
            self.quiz_data["wait_before_next"] = int(self.wait_time_var.get())
        except ValueError:
            messagebox.showwarning("Warning", "Display time and wait time must be numbers")
            return

        # Pre-fill the dialog with the previously loaded/saved file
        if self._loaded_filepath:
            init_dir  = os.path.dirname(self._loaded_filepath)
            init_file = os.path.basename(self._loaded_filepath)
        else:
            init_dir  = _SCRIPT_DIR
            init_file = "quizz_data.json"

        while True:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir=init_dir,
                initialfile=init_file,
            )
            if not filename:
                return  # user cancelled

            # If the chosen path is the same as the originally loaded file, confirm overwrite
            if (self._loaded_filepath and
                    os.path.abspath(filename) == os.path.abspath(self._loaded_filepath)):
                answer = messagebox.askyesnocancel(
                    "Overwrite?",
                    f"'{os.path.basename(filename)}' is the file you loaded.\n"
                    f"Overwrite it with the updated quiz?\n\n"
                    f"Yes = overwrite   No = choose a different name   Cancel = abort"
                )
                if answer is None:    # Cancel
                    return
                if answer is False:   # No — let user pick again
                    init_file = os.path.basename(filename)
                    continue
                # Yes — fall through and save

            try:
                with open(filename, 'w') as f:
                    json.dump(self.quiz_data, f, indent=2)
                self._loaded_filepath = os.path.abspath(filename)
                self._loaded_file_var.set(os.path.basename(filename))
                messagebox.showinfo("Saved", f"Quiz saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save quiz: {str(e)}")
            return
    
    def load_quiz(self):
        """Load quiz from JSON file"""
        init_dir = os.path.dirname(self._loaded_filepath) if self._loaded_filepath else _SCRIPT_DIR
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=init_dir,
            initialfile="quizz_data.json"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.quiz_data = json.load(f)
                self._loaded_filepath = os.path.abspath(filename)
                self._loaded_file_var.set(os.path.basename(filename))
                
                # Update UI
                self.display_time_var.set(str(self.quiz_data.get("display_time", 5)))
                self.wait_time_var.set(str(self.quiz_data.get("wait_before_next", 3)))
                
                self.refresh_questions_list()
                self.clear_current_question()
                
                messagebox.showinfo("Success", f"Loaded {len(self.quiz_data['questions'])} questions")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load quiz: {str(e)}")
    
    def new_quiz(self):
        """Start a new quiz"""
        if self.quiz_data["questions"]:
            if not messagebox.askyesno("Confirm", "Start a new quiz? Unsaved changes will be lost."):
                return
        
        self.quiz_data = {
            "display_time": 5,
            "wait_before_next": 3,
            "questions": []
        }
        self._loaded_filepath = None
        self._loaded_file_var.set("(no file loaded)")
        
        self.display_time_var.set("5")
        self.wait_time_var.set("3")
        self.questions_listbox.delete(0, tk.END)
        self.clear_current_question()
        
        messagebox.showinfo("Success", "New quiz created")

if __name__ == "__main__":
    app = QuizCreator()
    app.mainloop()