# © 2025 SREERAM A

import json
import os
import time
import csv
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from tkinter import ttk
from typing import List, Dict, Optional, Any


STORAGE_FILE = "tasks.json"
DATE_HINT = "YYYY-MM-DD"
PRIORITIES = ["Low", "Medium", "High"]


class Task:
	def __init__(self, task_id: int, text: str, completed: bool = False, created_at: float = None,
				priority: str = "Medium", due_date: str = "", tags: List[str] = None, order_index: int = 0):
		self.id = task_id
		self.text = text
		self.completed = completed
		self.created_at = created_at if created_at is not None else time.time()
		self.priority = priority if priority in PRIORITIES else "Medium"
		self.due_date = due_date
		self.tags = tags or []
		self.order_index = order_index

	def to_dict(self) -> Dict[str, Any]:
		return {
			"id": self.id,
			"text": self.text,
			"completed": self.completed,
			"created_at": self.created_at,
			"priority": self.priority,
			"due_date": self.due_date,
			"tags": self.tags,
			"order_index": self.order_index,
		}

	@staticmethod
	def from_dict(data: Dict[str, Any]) -> "Task":
		return Task(
			task_id=data.get("id", int(time.time() * 1000)),
			text=data.get("text", ""),
			completed=data.get("completed", False),
			created_at=data.get("created_at", time.time()),
			priority=data.get("priority", "Medium"),
			due_date=data.get("due_date", ""),
			tags=data.get("tags", []) or [],
			order_index=data.get("order_index", 0),
		)


class TodoApp:
	def __init__(self, root: tk.Tk):
		self.root = root
		self.root.title("To-Do App")
		self.tasks: List[Task] = []

		self.filter_mode = tk.StringVar(value="All")  # All, Active, Completed
		self.filter_priority = tk.StringVar(value="All")  # All + PRIORITIES
		self.search_text = tk.StringVar(value="")
		self.dark_mode = tk.BooleanVar(value=False)

		self.undo_stack: List[List[Dict[str, Any]]] = []
		self.redo_stack: List[List[Dict[str, Any]]] = []

		self._init_style()
		self._build_menu()
		self._build_ui()
		self._load_tasks()
		self._refresh_tree()

		self.root.protocol("WM_DELETE_WINDOW", self._on_close)
		self._bind_shortcuts()

	def _init_style(self) -> None:
		self.style = ttk.Style(self.root)
		try:
			self.style.theme_use("clam")
		except Exception:
			pass
		self._apply_theme()

	def _apply_theme(self) -> None:
		if self.dark_mode.get():
			bg = "#1e1f22"
			fg = "#e6e6e6"
			accent = "#5e81ac"
			select_bg = "#404552"
			self.root.configure(bg=bg)
			self.style.configure("Treeview", background=bg, fieldbackground=bg, foreground=fg)
			self.style.map("Treeview", background=[("selected", select_bg)])
			self.style.configure("TLabel", background=bg, foreground=fg)
			self.style.configure("TFrame", background=bg)
			self.style.configure("TEntry", fieldbackground="#2b2d31", foreground=fg)
			self.style.configure("TButton", background=bg, foreground=fg)
			self.style.configure("TRadiobutton", background=bg, foreground=fg)
			self.style.configure("TCheckbutton", background=bg, foreground=fg)
		else:
			# reset to defaults
			self.root.configure(bg="SystemButtonFace")
			self.style.theme_use("clam")

	def _build_menu(self) -> None:
		menubar = tk.Menu(self.root)

		file_menu = tk.Menu(menubar, tearoff=0)
		file_menu.add_command(label="Import JSON", command=self.import_json)
		file_menu.add_command(label="Export JSON", command=self.export_json)
		file_menu.add_separator()
		file_menu.add_command(label="Import CSV", command=self.import_csv)
		file_menu.add_command(label="Export CSV", command=self.export_csv)
		file_menu.add_separator()
		file_menu.add_command(label="Exit", command=self._on_close)
		menubar.add_cascade(label="File", menu=file_menu)

		view_menu = tk.Menu(menubar, tearoff=0)
		view_menu.add_checkbutton(label="Dark Mode", onvalue=True, offvalue=False, variable=self.dark_mode, command=self._on_toggle_dark)
		menubar.add_cascade(label="View", menu=view_menu)

		help_menu = tk.Menu(menubar, tearoff=0)
		help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)
		help_menu.add_command(label="About", command=self._show_about)
		menubar.add_cascade(label="Help", menu=help_menu)

		self.root.config(menu=menubar)

	def _build_ui(self) -> None:
		# Top: add controls
		add_frame = ttk.Frame(self.root)
		add_frame.pack(fill=tk.X, padx=10, pady=(10, 6))

		self.add_entry = ttk.Entry(add_frame)
		self.add_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
		self.add_entry.bind("<Return>", lambda _e: self.add_task())

		self.priority_box = ttk.Combobox(add_frame, values=PRIORITIES, state="readonly", width=8)
		self.priority_box.set("Medium")
		self.priority_box.pack(side=tk.LEFT, padx=6)

		self.due_entry = ttk.Entry(add_frame, width=12)
		self.due_entry.insert(0, DATE_HINT)
		self.due_entry.pack(side=tk.LEFT, padx=6)

		self.tags_entry = ttk.Entry(add_frame, width=18)
		self.tags_entry.insert(0, "tags,comma,separated")
		self.tags_entry.pack(side=tk.LEFT, padx=6)

		add_btn = ttk.Button(add_frame, text="Add", command=self.add_task)
		add_btn.pack(side=tk.LEFT, padx=6)

		# Search + filters
		filter_frame = ttk.Frame(self.root)
		filter_frame.pack(fill=tk.X, padx=10, pady=(0, 6))

		search_label = ttk.Label(filter_frame, text="Search:")
		search_label.pack(side=tk.LEFT)
		search_entry = ttk.Entry(filter_frame, textvariable=self.search_text, width=24)
		search_entry.pack(side=tk.LEFT, padx=(4, 10))
		search_entry.bind("<KeyRelease>", lambda _e: self._refresh_tree())

		for mode in ("All", "Active", "Completed"):
			rb = ttk.Radiobutton(filter_frame, text=mode, value=mode, variable=self.filter_mode, command=self._refresh_tree)
			rb.pack(side=tk.LEFT, padx=3)

		priority_opts = ["All"] + PRIORITIES
		prio_label = ttk.Label(filter_frame, text="Priority:")
		prio_label.pack(side=tk.LEFT, padx=(10, 0))
		prio_combo = ttk.Combobox(filter_frame, values=priority_opts, textvariable=self.filter_priority, state="readonly", width=8)
		prio_combo.current(0)
		prio_combo.pack(side=tk.LEFT, padx=4)
		prio_combo.bind("<<ComboboxSelected>>", lambda _e: self._refresh_tree())

		clear_btn = ttk.Button(filter_frame, text="Clear Filters", command=self._clear_filters)
		clear_btn.pack(side=tk.RIGHT)

		# Treeview
		tree_frame = ttk.Frame(self.root)
		tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

		scroll_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
		scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
		scroll_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
		scroll_x.pack(side=tk.BOTTOM, fill=tk.X)

		self.tree = ttk.Treeview(tree_frame, columns=("text", "due", "priority", "tags", "status"), show="headings", selectmode="extended", yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
		self.tree.heading("text", text="Task")
		self.tree.heading("due", text="Due")
		self.tree.heading("priority", text="Priority")
		self.tree.heading("tags", text="Tags")
		self.tree.heading("status", text="Status")
		self.tree.column("text", width=260, anchor=tk.W)
		self.tree.column("due", width=90, anchor=tk.CENTER)
		self.tree.column("priority", width=80, anchor=tk.CENTER)
		self.tree.column("tags", width=150, anchor=tk.W)
		self.tree.column("status", width=80, anchor=tk.CENTER)
		self.tree.pack(fill=tk.BOTH, expand=True)
		scroll_y.config(command=self.tree.yview)
		scroll_x.config(command=self.tree.xview)

		self.tree.bind("<Double-1>", lambda _e: self.edit_selected_task())
		self.tree.bind("<Delete>", lambda _e: self.delete_selected_tasks())
		self.tree.bind("<space>", lambda _e: self.toggle_selected_tasks())

		# Drag-and-drop reordering
		self.tree.bind("<ButtonPress-1>", self._on_tree_button_press)
		self.tree.bind("<B1-Motion>", self._on_tree_motion)
		self.tree.bind("<ButtonRelease-1>", self._on_tree_button_release)
		self._dragging_iid: Optional[str] = None

		# Bottom actions
		actions = ttk.Frame(self.root)
		actions.pack(fill=tk.X, padx=10, pady=(0, 10))

		btn_toggle = ttk.Button(actions, text="Toggle Complete", command=self.toggle_selected_tasks)
		btn_toggle.pack(side=tk.LEFT)

		btn_del = ttk.Button(actions, text="Delete", command=self.delete_selected_tasks)
		btn_del.pack(side=tk.LEFT, padx=6)

		btn_undo = ttk.Button(actions, text="Undo", command=self.undo)
		btn_undo.pack(side=tk.LEFT, padx=(16, 6))
		btn_redo = ttk.Button(actions, text="Redo", command=self.redo)
		btn_redo.pack(side=tk.LEFT)

	def _bind_shortcuts(self) -> None:
		self.root.bind("<Control-z>", lambda _e: self.undo())
		self.root.bind("<Control-y>", lambda _e: self.redo())
		self.root.bind("<Control-f>", lambda _e: self._focus_search())

	def _focus_search(self) -> None:
		for w in self.root.winfo_children():
			# naive focus to first entry matching search textvariable
			if isinstance(w, ttk.Frame):
				for c in w.winfo_children():
					if isinstance(c, ttk.Entry) and getattr(c, "cget", None) and c.cget("textvariable"):
						self.root.after(10, c.focus_set)
						return

	def _on_toggle_dark(self) -> None:
		self._apply_theme()

	def _clear_filters(self) -> None:
		self.filter_mode.set("All")
		self.filter_priority.set("All")
		self.search_text.set("")
		self._refresh_tree()

	def _save_snapshot(self) -> None:
		self.undo_stack.append([t.to_dict() for t in self.tasks])
		self.redo_stack.clear()

	def undo(self) -> None:
		if not self.undo_stack:
			return
		current = [t.to_dict() for t in self.tasks]
		prev = self.undo_stack.pop()
		self.redo_stack.append(current)
		self.tasks = [Task.from_dict(d) for d in prev]
		self._save_tasks()
		self._refresh_tree()

	def redo(self) -> None:
		if not self.redo_stack:
			return
		current = [t.to_dict() for t in self.tasks]
		next_state = self.redo_stack.pop()
		self.undo_stack.append(current)
		self.tasks = [Task.from_dict(d) for d in next_state]
		self._save_tasks()
		self._refresh_tree()

	def _save_tasks(self) -> None:
		try:
			# ensure order_index sequencing
			for idx, task in enumerate(sorted(self.tasks, key=lambda t: t.order_index)):
				task.order_index = idx
			with open(STORAGE_FILE, "w", encoding="utf-8") as f:
				json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
		except Exception as e:
			messagebox.showerror("Save Error", f"Failed to save tasks: {e}")

	def _load_tasks(self) -> None:
		if not os.path.exists(STORAGE_FILE):
			self.tasks = []
			return
		try:
			with open(STORAGE_FILE, "r", encoding="utf-8") as f:
				data = json.load(f)
				self.tasks = [Task.from_dict(item) for item in data if isinstance(item, dict)]
				# normalize order_index
				self.tasks.sort(key=lambda t: (t.order_index, t.created_at, t.id))
		except Exception:
			self.tasks = []

	def _filter_include(self, task: Task) -> bool:
		mode = self.filter_mode.get()
		if mode == "Active" and task.completed:
			return False
		if mode == "Completed" and not task.completed:
			return False
		prio = self.filter_priority.get()
		if prio != "All" and task.priority != prio:
			return False
		q = self.search_text.get().strip().lower()
		if q:
			hay = " ".join([task.text, task.due_date, task.priority, ",".join(task.tags)]).lower()
			if q not in hay:
				return False
		return True

	def _refresh_tree(self) -> None:
		for iid in self.tree.get_children():
			self.tree.delete(iid)
		for task in sorted(self.tasks, key=lambda t: (t.order_index, t.created_at, t.id)):
			if not self._filter_include(task):
				continue
			status = "Done" if task.completed else "Active"
			tags = ", ".join(task.tags)
			iid = str(task.id)
			self.tree.insert("", tk.END, iid=iid, values=(task.text, task.due_date, task.priority, tags, status))

	def _selected_task_ids(self) -> List[int]:
		ids: List[int] = []
		for iid in self.tree.selection():
			try:
				ids.append(int(iid))
			except Exception:
				pass
		return ids

	def add_task(self) -> None:
		text = self.add_entry.get().strip()
		if not text:
			return
		priority = self.priority_box.get() or "Medium"
		due = self.due_entry.get().strip()
		if due == DATE_HINT:
			due = ""
		tags_text = self.tags_entry.get().strip()
		tags = [t.strip() for t in tags_text.split(",") if t.strip()] if tags_text else []
		new_id = int(time.time() * 1000)
		order_index = len(self.tasks)
		self._save_snapshot()
		self.tasks.append(Task(new_id, text, False, time.time(), priority, due, tags, order_index))
		self.add_entry.delete(0, tk.END)
		self._save_tasks()
		self._refresh_tree()

	def edit_selected_task(self) -> None:
		ids = self._selected_task_ids()
		if not ids:
			return
		# Edit first selected task via dialog
		task = next((t for t in self.tasks if t.id == ids[0]), None)
		if not task:
			return
		new_text = simpledialog.askstring("Edit Task", "Task:", initialvalue=task.text, parent=self.root)
		if new_text is None:
			return
		new_text = new_text.strip()
		if not new_text:
			messagebox.showwarning("Validation", "Task text cannot be empty.")
			return
		new_due = simpledialog.askstring("Edit Due Date", f"Due date ({DATE_HINT}):", initialvalue=task.due_date, parent=self.root)
		if new_due is None:
			new_due = task.due_date
		new_pri = simpledialog.askstring("Edit Priority", f"Priority {PRIORITIES}:", initialvalue=task.priority, parent=self.root)
		if new_pri not in PRIORITIES:
			new_pri = task.priority
		new_tags = simpledialog.askstring("Edit Tags", "tags,comma,separated:", initialvalue=",".join(task.tags), parent=self.root)
		if new_tags is None:
			new_tags_list = task.tags
		else:
			new_tags_list = [t.strip() for t in new_tags.split(",") if t.strip()]
		self._save_snapshot()
		task.text = new_text
		task.due_date = new_due or ""
		task.priority = new_pri
		task.tags = new_tags_list
		self._save_tasks()
		self._refresh_tree()

	def delete_selected_tasks(self) -> None:
		ids = set(self._selected_task_ids())
		if not ids:
			return
		self._save_snapshot()
		self.tasks = [t for t in self.tasks if t.id not in ids]
		# reassign order
		for idx, t in enumerate(sorted(self.tasks, key=lambda x: x.order_index)):
			t.order_index = idx
		self._save_tasks()
		self._refresh_tree()

	def toggle_selected_tasks(self) -> None:
		ids = set(self._selected_task_ids())
		if not ids:
			return
		self._save_snapshot()
		for t in self.tasks:
			if t.id in ids:
				t.completed = not t.completed
		self._save_tasks()
		self._refresh_tree()

	# Drag-and-drop reordering handlers
	def _on_tree_button_press(self, event) -> None:
		row = self.tree.identify_row(event.y)
		self._dragging_iid = row if row else None

	def _on_tree_motion(self, event) -> None:
		if not self._dragging_iid:
			return
		row_under = self.tree.identify_row(event.y)
		if row_under and row_under != self._dragging_iid:
			index_under = self.tree.index(row_under)
			self.tree.move(self._dragging_iid, "", index_under)

	def _on_tree_button_release(self, _event) -> None:
		if not self._dragging_iid:
			return
		# Apply visual order to task.order_index
		self._save_snapshot()
		ordered_ids = [int(i) for i in self.tree.get_children("")]
		order_map = {task_id: idx for idx, task_id in enumerate(ordered_ids)}
		for t in self.tasks:
			if t.id in order_map:
				t.order_index = order_map[t.id]
		self._dragging_iid = None
		self._save_tasks()
		self._refresh_tree()

	def import_json(self) -> None:
		path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
		if not path:
			return
		try:
			with open(path, "r", encoding="utf-8") as f:
				data = json.load(f)
				if not isinstance(data, list):
					raise ValueError("Invalid JSON format")
				self._save_snapshot()
				self.tasks = [Task.from_dict(item) for item in data if isinstance(item, dict)]
				self._save_tasks()
				self._refresh_tree()
		except Exception as e:
			messagebox.showerror("Import JSON", f"Failed to import: {e}")

	def export_json(self) -> None:
		path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")])
		if not path:
			return
		try:
			with open(path, "w", encoding="utf-8") as f:
				json.dump([t.to_dict() for t in self.tasks], f, ensure_ascii=False, indent=2)
		except Exception as e:
			messagebox.showerror("Export JSON", f"Failed to export: {e}")

	def import_csv(self) -> None:
		path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
		if not path:
			return
		try:
			with open(path, "r", encoding="utf-8", newline="") as f:
				reader = csv.DictReader(f)
				self._save_snapshot()
				self.tasks = []
				for row in reader:
					text = row.get("text", "")
					completed = row.get("completed", "").strip().lower() in ("1", "true", "yes", "y")
					priority = row.get("priority", "Medium")
					due = row.get("due_date", "")
					tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
					order_index = int(row.get("order_index", len(self.tasks)))
					self.tasks.append(Task(int(time.time() * 1000) + len(self.tasks), text, completed, time.time(), priority, due, tags, order_index))
				self._save_tasks()
				self._refresh_tree()
		except Exception as e:
			messagebox.showerror("Import CSV", f"Failed to import: {e}")

	def export_csv(self) -> None:
		path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
		if not path:
			return
		try:
			with open(path, "w", encoding="utf-8", newline="") as f:
				fieldnames = ["id", "text", "completed", "created_at", "priority", "due_date", "tags", "order_index"]
				writer = csv.DictWriter(f, fieldnames=fieldnames)
				writer.writeheader()
				for t in self.tasks:
					row = t.to_dict()
					row["tags"] = ",".join(row.get("tags", []))
					writer.writerow(row)
		except Exception as e:
			messagebox.showerror("Export CSV", f"Failed to export: {e}")

	def _show_shortcuts(self) -> None:
		text = (
			"Enter: Add task\n"
			"Space: Toggle complete (selected)\n"
			"Delete: Delete selected\n"
			"Ctrl+Z: Undo\n"
			"Ctrl+Y: Redo\n"
			"Ctrl+F: Focus search\n"
			"Double-click: Edit task\n"
			"Drag rows: Reorder tasks"
		)
		messagebox.showinfo("Shortcuts", text)

	def _show_about(self) -> None:
		messagebox.showinfo("About", "To-Do App\n\n© 2025 SREERAM A")

	def _on_close(self) -> None:
		self._save_tasks()
		self.root.destroy()


def main() -> None:
	root = tk.Tk()
	root.minsize(640, 480)
	app = TodoApp(root)
	root.mainloop()


if __name__ == "__main__":
	main()
