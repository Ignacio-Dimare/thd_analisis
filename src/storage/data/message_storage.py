# storage/data/message_store.py

class MessageStore:
    def __init__(self):
        self._messages = []
        self._listeners = []

    def add_message(self, sender, text):
        self._messages.append({"from": sender, "text": text})
        self._notify()

    def get_messages(self):
        return self._messages

    def subscribe(self, listener):
        self._listeners.append(listener)

    def _notify(self):
        for fn in self._listeners:
            fn()

