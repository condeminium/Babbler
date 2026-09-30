import os
import pathlib
import pickle
import random
from typing import Dict, List, Optional
import threading

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class TTSHandler:
    """Handles TTS initialisation and runs on separate thread to main loop."""

    def __init__(self, enabled: bool = True, rate: int = 175, volume: float = 1.0):
        self.enabled = enabled and HAS_PYTTSX3
        self.rate = rate
        self.volume = volume

        if not HAS_PYTTSX3 and enabled:
            print("[Warning] 'pyttsx3' module not found. Run 'pip install pyttsx3' to enable TTS.")

    def _speak_thread(self, text: str) -> None:
        """Instantiates TTS thread."""
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            engine.setProperty("volume", self.volume)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[TTS Error] {e}")

    def speak(self, text: str) -> None:
        """Speak the string asynchronously if TTS is enabled and text is valid."""
        if not self.enabled:
            return

        clean_text = text.strip()
        if clean_text in ("...", ""):
            return

        thread = threading.Thread(target=self._speak_thread, args=(clean_text,), daemon=True)
        thread.start()

class WordNode:
    """Tracks a single word entry and its reply associations."""

    def __init__(self, name: str, initial_replies: Optional[List[str]] = None):
        self.name: str = name
        self.replies: List[str] = (
            initial_replies if initial_replies is not None else [name]
        )
        self.uses: int = 0

    def add_associations(self, words: List[str]) -> None:
        self.replies.extend(words)

    def deduplicate(self) -> None:
        self.replies = list(set(self.replies))

    def limit_replies(self, max_replies: int) -> None:
        if len(self.replies) > max_replies:
            self.replies = random.sample(self.replies, max_replies)

    def generate_associations(self, max_samples: int = 3) -> List[str]:
        if not self.replies:
            return []
        count = random.randint(0, max_samples)
        self.uses += count
        return [random.choice(self.replies) for _ in range(count)]


class StorageHandler:
    """Manages disk persistence via pickle."""

    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path

    def load(self) -> Dict[str, WordNode]:
        if not self.file_path.exists():
            print("Memory file not found. Starting with fresh memory.")
            return {}
        try:
            with open(self.file_path, "rb") as f:
                memory = pickle.load(f)
            print("Memory file loaded.")
            return memory
        except Exception as error:
            print(f"Error loading memory file ({error}). Starting empty.")
            return {}

    def save(self, memory: Dict[str, WordNode]) -> None:
        try:
            with open(self.file_path, "wb") as f:
                pickle.dump(memory, f)
            print("Memory saved successfully.")
        except Exception as error:
            print(f"Error saving memory: {error}")


class MemoryBank:
    """Handles memory pruning and word associations."""

    def __init__(
        self,
        storage_path: pathlib.Path,
        max_words: int = 1000,
        max_responses_per_word: int = 15,
        deduplicate: bool = True,
    ):
        self.storage = StorageHandler(storage_path)
        self.max_words = max_words
        self.max_responses_per_word = max_responses_per_word
        self.deduplicate = deduplicate
        self.nodes: Dict[str, WordNode] = self.storage.load()

    def get_or_create(self, word: str) -> WordNode:
        if word not in self.nodes:
            self.nodes[word] = WordNode(word)
        return self.nodes[word]

    def associate_words(
        self, source_words: List[str], target_words: List[str]
    ) -> None:
        if not target_words:
            return
        for word in source_words:
            if word in self.nodes:
                self.nodes[word].add_associations(target_words)

    def prune(self) -> None:
        for node in self.nodes.values():
            if self.deduplicate:
                node.deduplicate()
            node.limit_replies(self.max_responses_per_word)

        if len(self.nodes) > self.max_words:
            total_uses = sum(node.uses for node in self.nodes.values())
            avg_uses = total_uses / len(self.nodes) if self.nodes else 0
            candidates = [
                word
                for word, node in self.nodes.items()
                if node.uses <= avg_uses
            ]

            for word in candidates:
                if len(self.nodes) <= self.max_words:
                    break
                del self.nodes[word]

    def save(self) -> None:
        self.storage.save(self.nodes)


class Babbler:
    """Manages bot execution loop, terminal I/O, speech, and runtime state."""

    HELP_MESSAGE = """Commands:
  #help - Display help
  #tts  - Toggle Text-to-Speech on/off
  #quit - Save and exit
"""

    def __init__(
        self,
        memory_file: str = "memory.data",
        auto_save: bool = True,
        save_interval: int = 25,
        max_words: int = 1000,
        max_responses_per_word: int = 15,
        deduplicate: bool = True,
        enable_tts: bool = True,
    ):
        self.auto_save = auto_save
        self.save_interval = save_interval
        self.session_count = 0

        self._clear_screen()
        print("Babbler bot initialized.")

        self.memory_bank = MemoryBank(
            storage_path=pathlib.Path(memory_file),
            max_words=max_words,
            max_responses_per_word=max_responses_per_word,
            deduplicate=deduplicate,
        )
        self.tts = TTSHandler(enabled=enable_tts)

    @staticmethod
    def _clear_screen() -> None:
        os.system("cls" if os.name == "nt" else "clear")

    def talk(self) -> None:
        previous_response_tokens: List[str] = []

        try:
            while True:
                if self.auto_save:
                    self.session_count += 1
                    if self.session_count >= self.save_interval:
                        self.session_count = 0
                        self.memory_bank.save()

                self.memory_bank.prune()

                raw_input = input("You: ").strip()

                if raw_input.startswith("#"):
                    cmd = raw_input.lower()
                    if "#quit" in cmd:
                        break
                    elif "#help" in cmd:
                        print(self.HELP_MESSAGE)
                    elif "#tts" in cmd:
                        self.tts.enabled = not self.tts.enabled
                        state = "enabled" if self.tts.enabled else "disabled"
                        print(f"TTS is now {state}.")
                    continue

                input_tokens = raw_input.lower().split()
                if not input_tokens:
                    continue

                self.memory_bank.associate_words(
                    previous_response_tokens, input_tokens
                )

                response_tokens: List[str] = []
                for word in input_tokens:
                    node = self.memory_bank.get_or_create(word)
                    response_tokens.extend(node.generate_associations())

                answer = (
                    " ".join(response_tokens) if response_tokens else "..."
                )
                print(f"Babbler: {answer}")

                # Speak the response audio
                self.tts.speak(answer)

                previous_response_tokens = answer.split()

        finally:
            self.memory_bank.save()


if __name__ == "__main__":
    bot = Babbler(enable_tts=True)
    bot.talk()