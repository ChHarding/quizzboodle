import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
from PIL import Image, ImageTk
import os

class QuizCreator(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Quiz Creator")
        self.geometry("900x600")
        
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
        
        self.setup_ui()
        
    def setup_ui(self):
        # Title
        title = ttk.Label(self, text="Quiz Creator", font=('Arial', 16, 'bold'))
        title.pack(pady=10)
        
        # Create notebook (tab container)
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create tabs
        settings_tab = ttk.Frame(notebook, padding="10")
        question_tab = ttk.Frame(notebook, padding="10")
        questions_list_tab = ttk.Frame(notebook, padding="10")
        file_tab = ttk.Frame(notebook, padding="10")
        
        notebook.add(settings_tab, text="Quiz Settings")
        notebook.add(question_tab, text="Create Question")
        notebook.add(questions_list_tab, text="Questions in Quiz")
        notebook.add(file_tab, text="File Operations")
        
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
        
        ttk.Button(question_frame, text="Add Question Image", command=self.add_question_image).grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.question_image_label = ttk.Label(question_frame, text="No image selected")
        self.question_image_label.grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Answers Section (same tab)
        answers_frame = ttk.LabelFrame(question_tab, text="Answers", padding="10")
        answers_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Answer entry
        ttk.Label(answers_frame, text="Answer Text:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.answer_text_var = tk.StringVar()
        ttk.Entry(answers_frame, textvariable=self.answer_text_var, width=40).grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(answers_frame, text="Add Answer Image", command=self.add_answer_image).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.answer_image_label = ttk.Label(answers_frame, text="No image selected")
        self.answer_image_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(answers_frame, text="Add Answer", command=self.add_answer, style="Accent.TButton").grid(row=2, column=0, columnspan=2, pady=10)
        
        # Answers list
        ttk.Label(answers_frame, text="Current Answers:").grid(row=3, column=0, sticky=tk.W, padx=5)
        
        # Frame for answers list with scrollbar
        list_frame = ttk.Frame(answers_frame)
        list_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.answers_listbox = tk.Listbox(list_frame, height=6, width=50, yscrollcommand=scrollbar.set)
        self.answers_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.answers_listbox.yview)
        
        # Correct answer selection
        ttk.Label(answers_frame, text="Correct Answer Index (0-based):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.correct_index_var = tk.StringVar(value="0")
        ttk.Entry(answers_frame, textvariable=self.correct_index_var, width=10).grid(row=5, column=1, sticky=tk.W, padx=5)
        
        ttk.Button(answers_frame, text="Remove Selected Answer", command=self.remove_answer).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Question Management buttons (same tab)
        management_frame = ttk.Frame(question_tab)
        management_frame.pack(pady=10)
        
        ttk.Button(management_frame, text="Add Question to Quiz", command=self.add_question_to_quiz, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
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
        
        ttk.Button(questions_frame, text="Remove Selected Question", command=self.remove_question).pack(pady=5)
        
        # === TAB 4: File Operations ===
        file_frame = ttk.LabelFrame(file_tab, text="File Management", padding="20")
        file_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Button(file_frame, text="Load Quiz", command=self.load_quiz, width=20).pack(pady=10)
        ttk.Button(file_frame, text="Save Quiz", command=self.save_quiz, width=20).pack(pady=10)
        ttk.Button(file_frame, text="New Quiz", command=self.new_quiz, width=20).pack(pady=10)
        
        ttk.Label(file_frame, text="Use these buttons to load, save, or create a new quiz.", 
                 foreground="gray").pack(pady=20)
        
        # Store temporary image paths
        self.temp_question_image = ""
        self.temp_answer_image = ""
        
    def add_question_image(self):
        """Browse and select question image"""
        filename = filedialog.askopenfilename(
            title="Select Question Image",
            initialdir="images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if filename:
            # Always convert to relative path if possible
            try:
                self.temp_question_image = os.path.relpath(filename)
            except ValueError:
                # Different drives on Windows, keep absolute
                self.temp_question_image = filename
            self.question_image_label.config(text=os.path.basename(filename))
    
    def add_answer_image(self):
        """Browse and select answer image"""
        filename = filedialog.askopenfilename(
            title="Select Answer Image",
            initialdir="images",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"), ("All files", "*.*")]
        )
        if filename:
            # Always convert to relative path if possible
            try:
                self.temp_answer_image = os.path.relpath(filename)
            except ValueError:
                # Different drives on Windows, keep absolute
                self.temp_answer_image = filename
            self.answer_image_label.config(text=os.path.basename(filename))
    
    def add_answer(self):
        """Add answer to current question"""
        text = self.answer_text_var.get().strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter answer text")
            return
        
        answer = {"text": text}
        if self.temp_answer_image:
            answer["image"] = self.temp_answer_image
        
        self.current_answers.append(answer)
        
        # Update listbox
        display_text = f"{len(self.current_answers)-1}: {text}"
        if self.temp_answer_image:
            display_text += f" [Image: {os.path.basename(self.temp_answer_image)}]"
        self.answers_listbox.insert(tk.END, display_text)
        
        # Clear inputs
        self.answer_text_var.set("")
        self.temp_answer_image = ""
        self.answer_image_label.config(text="No image selected")
    
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
    
    def add_question_to_quiz(self):
        """Add current question to quiz"""
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
        
        # Build question object
        question = {
            "question": question_text,
            "answers": self.current_answers.copy(),
            "correct_answer_index": correct_index
        }
        
        if self.temp_question_image:
            question["question_image"] = self.temp_question_image
        
        self.quiz_data["questions"].append(question)
        
        # Update questions listbox
        display_text = f"Q{len(self.quiz_data['questions'])}: {question_text[:50]}"
        if len(question_text) > 50:
            display_text += "..."
        self.questions_listbox.insert(tk.END, display_text)
        
        # Clear current question
        self.clear_current_question()
        
        messagebox.showinfo("Success", "Question added to quiz!")
    
    def clear_current_question(self):
        """Clear current question inputs"""
        self.question_text.delete("1.0", tk.END)
        self.temp_question_image = ""
        self.question_image_label.config(text="No image selected")
        self.current_answers = []
        self.answers_listbox.delete(0, tk.END)
        self.answer_text_var.set("")
        self.temp_answer_image = ""
        self.answer_image_label.config(text="No image selected")
        self.correct_index_var.set("0")
    
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
        """Save quiz to JSON file"""
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
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="quizz_data.json"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.quiz_data, f, indent=2)
                messagebox.showinfo("Success", f"Quiz saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save quiz: {str(e)}")
    
    def load_quiz(self):
        """Load quiz from JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="quizz_data.json"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    self.quiz_data = json.load(f)
                
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
        
        self.display_time_var.set("5")
        self.wait_time_var.set("3")
        self.questions_listbox.delete(0, tk.END)
        self.clear_current_question()
        
        messagebox.showinfo("Success", "New quiz created")

if __name__ == "__main__":
    app = QuizCreator()
    app.mainloop()
