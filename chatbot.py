import os
import pathlib
import pickle
import random
import threading
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

# try import tts lib if user got it installed
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


# handles talking out loud using tts
class TTSHandler:
    def __init__(self, enabled: bool = True, rate: int = 175, volume: float = 1.0):
        self.enabled = enabled and HAS_PYTTSX3
        self.rate = rate
        self.volume = volume

        # yell at user if pyttsx3 missing
        if not HAS_PYTTSX3 and enabled:
            print("[Warning] 'pyttsx3' module not found. Run 'pip install pyttsx3' to enable TTS.")

    # this runs voice in separate thread so program dont freeze up
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

    # call this to say stuff out loud
    def speak(self, text: str) -> None:
        if not self.enabled:
            return

        clean_text = text.strip()
        if clean_text in ("...", ""):
            return

        # make background thread and start it up
        thread = threading.Thread(target=self._speak_thread, args=(clean_text,), daemon=True)
        thread.start()


# main markov chain stuff that learn word orders
class MarkovChain:
    START_TOKEN = "[START]"
    END_TOKEN = "[END]"

    def __init__(self, order: int = 2):
        self.order = order # how many word to look back
        self.chain: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)

    # teach the chain new sentences
    def train(self, tokens: List[str]) -> None:
        if len(tokens) < 1:
            return

        # pad start and end so it know where sentence begin and finish
        padded_tokens = ([self.START_TOKEN] * self.order) + tokens + [self.END_TOKEN]

        # slide through words and count what comes next
        for i in range(len(padded_tokens) - self.order):
            state = tuple(padded_tokens[i : i + self.order])
            next_word = padded_tokens[i + self.order]
            self.chain[state][next_word] += 1

    # make a new sentence based on what it learned
    def generate(self, seed_tokens: Optional[List[str]] = None, max_length: int = 30) -> str:
        if not self.chain:
            return "..."

        state = None
        # try start from end of user input if possible
        if seed_tokens and len(seed_tokens) >= self.order:
            potential_state = tuple(seed_tokens[-self.order:])
            if potential_state in self.chain:
                state = potential_state

        # fallback to start token or random state if seed not in chain
        if state is None:
            state = tuple([self.START_TOKEN] * self.order)
            if state not in self.chain:
                state = random.choice(list(self.chain.keys()))

        output: List[str] = []

        # build sentence word by word
        for _ in range(max_length):
            transitions = self.chain.get(state)
            if not transitions:
                break

            # pick next word weighted by how often it seen it
            words = list(transitions.keys())
            weights = list(transitions.values())
            next_word = random.choices(words, weights=weights, k=1)[0]

            # stop if sentence ended
            if next_word == self.END_TOKEN:
                break

            output.append(next_word)
            # shift state window forward one word
            state = tuple(list(state[1:]) + [next_word])

        return " ".join(output) if output else "..."


# handles saving and loading model to hard drive
class StorageHandler:
    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path

    # load binary pickle memory
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

    # save binary pickle memory
    def save(self, model: MarkovChain) -> None:
        try:
            with open(self.file_path, "wb") as f:
                pickle.dump(model, f)
            print("Markov memory saved successfully.")
        except Exception as error:
            print(f"Error saving memory: {error}")


# main bot controller class
class Babbler:
    HELP_MESSAGE = """Commands:
  #help - Display help
  #tts  - Toggle Text-to-Speech on/off
  #quit - Save and exit
"""

    def __init__(
        self,
        memory_file: str = "markov_memory.data",
        corpus_file: Optional[str] = "corpus.txt",
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

        # load old memory if exist
        self.storage = StorageHandler(pathlib.Path(memory_file))
        self.markov = self.storage.load()
        if not hasattr(self.markov, "order"):
            self.markov.order = order

        # read corpus text file if user gave one
        if corpus_file:
            self.train_from_file(corpus_file)

        self.tts = TTSHandler(enabled=enable_tts)

    # clear terminal output
    @staticmethod
    def _clear_screen() -> None:
        os.system("cls" if os.name == "nt" else "clear")

    # reads text file and trains model line by line
    def train_from_file(self, file_path: str) -> None:
        path = pathlib.Path(file_path)
        if not path.exists():
            print(f"[Warning] Training file '{file_path}' not found.")
            return

        print(f"Reading and training on '{file_path}'...")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        lines = text.replace("\r", "").split("\n")
        trained_count = 0

        # feed every line into markov chain
        for line in lines:
            tokens = line.lower().strip().split()
            if tokens:
                self.markov.train(tokens)
                trained_count += 1

        print(f"Training complete. Processed {trained_count} lines.")

    # main loop where user chat with bot
    def talk(self) -> None:
        previous_response_tokens: List[str] = []

        try:
            while True:
                # autosave every few messages
                if self.auto_save:
                    self.session_count += 1
                    if self.session_count >= self.save_interval:
                        self.session_count = 0
                        self.storage.save(self.markov)

                raw_input = input("You: ").strip()

                # handle hashtag commands
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

                # learn user input
                self.markov.train(input_tokens)

                # connect bot last output with user new input
                if previous_response_tokens:
                    self.markov.train(previous_response_tokens + input_tokens)

                # make answer and print it
                answer = self.markov.generate(seed_tokens=input_tokens)
                print(f"Babbler: {answer}")

                # say it out loud
                self.tts.speak(answer)

                previous_response_tokens = answer.split()

        finally:
            # save memory when exiting
            self.storage.save(self.markov)


# run bot if script executed directly
if __name__ == "__main__":
    bot = Babbler(corpus_file="corpus.txt", enable_tts=True, order=2)
    bot.talk()