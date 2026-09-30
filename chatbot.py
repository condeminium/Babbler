import os
import pathlib
import pickle
import random
import threading
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class TTSHandler:
    def __init__(self, enabled: bool = True, rate: int = 175, volume: float = 1.0):
        self.enabled = enabled and HAS_PYTTSX3
        self.rate = rate
        self.volume = volume

        if not HAS_PYTTSX3 and enabled:
            print("[Warning] 'pyttsx3' module not found. Run 'pip install pyttsx3' to enable TTS.")

    def _speak_thread(self, text: str) -> None:
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
        if not self.enabled:
            return

        clean_text = text.strip()
        if clean_text in ("...", ""):
            return

        thread = threading.Thread(target=self._speak_thread, args=(clean_text,), daemon=True)
        thread.start()


class MarkovChain:
    START_TOKEN = "[START]"
    END_TOKEN = "[END]"

    def __init__(self, order: int = 2):
        self.order = order
        self.chain: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)

    def train(self, tokens: List[str]) -> None:
        if len(tokens) < 1:
            return

        padded_tokens = ([self.START_TOKEN] * self.order) + tokens + [self.END_TOKEN]

        for i in range(len(padded_tokens) - self.order):
            state = tuple(padded_tokens[i : i + self.order])
            next_word = padded_tokens[i + self.order]
            self.chain[state][next_word] += 1

    def generate(self, seed_tokens: Optional[List[str]] = None, max_length: int = 30) -> str:
        if not self.chain:
            return "..."

        state = None
        if seed_tokens and len(seed_tokens) >= self.order:
            potential_state = tuple(seed_tokens[-self.order:])
            if potential_state in self.chain:
                state = potential_state

        if state is None:
            state = tuple([self.START_TOKEN] * self.order)
            if state not in self.chain:
                state = random.choice(list(self.chain.keys()))

        output: List[str] = []

        for _ in range(max_length):
            transitions = self.chain.get(state)
            if not transitions:
                break

            words = list(transitions.keys())
            weights = list(transitions.values())
            next_word = random.choices(words, weights=weights, k=1)[0]

            if next_word == self.END_TOKEN:
                break

            output.append(next_word)
            state = tuple(list(state[1:]) + [next_word])

        return " ".join(output) if output else "..."


class StorageHandler:
    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path

    def load(self) -> MarkovChain:
        if not self.file_path.exists():
            print("Memory file not found. Initializing fresh Markov model.")
            return MarkovChain()
        try:
            with open(self.file_path, "rb") as f:
                model = pickle.load(f)
            print("Markov memory loaded successfully.")
            return model
        except Exception as error:
            print(f"Error loading memory ({error}). Starting empty.")
            return MarkovChain()

    def save(self, model: MarkovChain) -> None:
        try:
            with open(self.file_path, "wb") as f:
                pickle.dump(model, f)
            print("Markov memory saved successfully.")
        except Exception as error:
            print(f"Error saving memory: {error}")


class Babbler:
    HELP_MESSAGE = """Commands:
  #help - Display help
  #tts  - Toggle Text-to-Speech on/off
  #quit - Save and exit
"""

    def __init__(
        self,
        memory_file: str = "markov_memory.data",
        order: int = 2,
        auto_save: bool = True,
        save_interval: int = 10,
        enable_tts: bool = True,
    ):
        self.auto_save = auto_save
        self.save_interval = save_interval
        self.session_count = 0

        self._clear_screen()
        print("Markov Babbler bot initialized.")

        self.storage = StorageHandler(pathlib.Path(memory_file))
        self.markov = self.storage.load()
        if not hasattr(self.markov, "order"):
            self.markov.order = order

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
                        self.storage.save(self.markov)

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

                self.markov.train(input_tokens)

                if previous_response_tokens:
                    self.markov.train(previous_response_tokens + input_tokens)

                answer = self.markov.generate(seed_tokens=input_tokens)
                print(f"Babbler: {answer}")

                self.tts.speak(answer)

                previous_response_tokens = answer.split()

        finally:
            self.storage.save(self.markov)


if __name__ == "__main__":
    bot = Babbler(enable_tts=True, order=2)
    bot.talk()