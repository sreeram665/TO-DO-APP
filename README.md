# Python To-Do App (Tkinter)

A simple desktop To-Do application built with Python's Tkinter. Tasks are saved to `tasks.json` automatically.

## Features
- Add, edit, delete tasks
- Mark tasks as completed/incomplete
- Filter: All / Active / Completed
- Persistent storage in `tasks.json`
- Keyboard shortcuts: Enter (add), Space (toggle), Delete (delete), Double-click (edit)

## Requirements
- Python 3.8+
- Tkinter (bundled with most standard Python installs)

## Run
```bash
python app.py
```

If you have multiple Python versions, try:
```bash
py app.py
```

## Project Structure
- `app.py`: Main Tkinter application
- `tasks.json`: Auto-created JSON storage file

## Notes
- The app saves after each change and also on exit.
- The UI uses a Listbox; completed tasks show as `[x]` and active as `[ ]`.

## Copyright
© 2025 SREERAM A
