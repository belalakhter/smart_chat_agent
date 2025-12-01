import threading
from collections import defaultdict
class NotesRunner:
    def __init__(self):
        self.user_notes = defaultdict(list)
        self.lock = threading.Lock()

    def add_note(self, user_id, note):
        with self.lock:
            self.user_notes[user_id].append(note)
            thread = threading.Thread(target=self.clear_notes, args=(user_id,))
            thread.daemon = True
            thread.start()

    def get_notes(self, requesting_user_id):
            with self.lock:
                return self.user_notes[requesting_user_id]


    def clear_notes(self, user_id):
        with self.lock:
            if len(self.user_notes[user_id]) > 10:
                self.user_notes[user_id].clear()

notes_runner = NotesRunner()

def get_note_runner():
    return notes_runner
