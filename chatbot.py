import os
import pathlib
import pickle
import random
import threading
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

# Optional dependency handling for Text-to-Speech support
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False


class TTSHandler:
    """Manages asynchronous Text-to-Speech synthesis running on a separate thread."""

    def __init__(self, enabled: bool = True, rate: int = 175, volume: float = 1.0):
        self.enabled = enabled and HAS_PYTTSX3
        self.rate = rate
        self.volume = volume

        if not HAS_PYTTSX3 and enabled:
            print("[Warning] 'pyttsx3' module not found. Run 'pip install pyttsx3' to enable TTS.")

    def _speak_thread(self, text: str) -> None:
        """Worker thread function to process speech synthesis without blocking the main event loop."""
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
        """Triggers asynchronous speech generation if TTS is enabled and text is valid."""
        if not self.enabled:
            return

        clean_text = text.strip()
        if clean_text in ("...", ""):
            return

        thread = threading.Thread(target=self._speak_thread, args=(clean_text,), daemon=True)
        thread.start()


class MarkovChain:
    """Implements an N-gram Markov Chain state machine for probabilistic text generation."""

    START_TOKEN = "[START]"
    END_TOKEN = "[END]"

    def __init__(self, order: int = 2):
        self.order = order  # Number of precursor words defining a single state context
        self.chain: Dict[Tuple[str, ...], Counter] = defaultdict(Counter)

    def train(self, tokens: List[str]) -> None:
        """Updates transition frequency distributions given an input sequence of tokens."""
        if len(tokens) < 1:
            return

        # Pad tokens with start and end markers to capture sentence boundaries
        padded_tokens = ([self.START_TOKEN] * self.order) + tokens + [self.END_TOKEN]

        # Slide an N-gram window across tokens to build state transition frequencies
        for i in range(len(padded_tokens) - self.order):
            state = tuple(padded_tokens[i : i + self.order])
            next_word = padded_tokens[i + self.order]
            self.chain[state][next_word] += 1

    def generate(self, seed_tokens: Optional[List[str]] = None, max_length: int = 30) -> str:
        """Generates text via weighted random walks along observed state transitions."""
        if not self.chain:
            return "..."

        state = None
        # Attempt to seed initial state using the trailing tokens of user input
        if seed_tokens and len(seed_tokens) >= self.order:
            potential_state = tuple(seed_tokens[-self.order:])
            if potential_state in self.chain:
                state = potential_state

        # Fall back to default start state or a random state if seed is unmapped
        if state is None:
            state = tuple([self.START_TOKEN] * self.order)
            if state not in self.chain:
                state = random.choice(list(self.chain.keys()))

        output: List[str] = []

        # Traverse transition network up to max_length steps or terminal token
        for _ in range(max_length):
            transitions = self.chain.get(state)
            if not transitions:
                break

            # Perform weighted selection based on observed token frequencies
            words = list(transitions.keys())
            weights = list(transitions.values())
            next_word = random.choices(words, weights=weights, k=1)[0]

            if next_word == self.END_TOKEN:
                break

            output.append(next_word)
            # Advance state window forward by one token
            state = tuple(list(state[1:]) + [next_word])

        return " ".join(output) if output else "..."


class StorageHandler:
    """Handles object serialization and disk persistence for the Markov chain state."""

    def __init__(self, file_path: pathlib.Path):
        self.file_path = file_path

    def load(self) -> MarkovChain:
        """Loads serialized model data from disk or initializes a new MarkovChain instance."""
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
        """Serializes current Markov model state to disk using pickle."""
        try:
            with open(self.file_path, "wb") as f:
                pickle.dump(model, f)
            print("Markov memory saved successfully.")
        except Exception as error:
            print(f"Error saving memory: {error}")


class Babbler:
    """Core runtime coordinator managing user I/O, corpus training, and conversation loops."""

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

        self.storage = StorageHandler(pathlib.Path(memory_file))
        self.markov = self.storage.load()
        if not hasattr(self.markov, "order"):
            self.markov.order = order

        # Train model on external text corpus during initialization if provided
        if corpus_file:
            self.train_from_file(corpus_file)

        self.tts = TTSHandler(enabled=enable_tts)

    @staticmethod
    def _clear_screen() -> None:
        """Clears the terminal display buffer for platform independence."""
        os.system("cls" if os.name == "nt" else "clear")

    def train_from_file(self, file_path: str) -> None:
        """Parses a target plain-text file line-by-line to update transition probabilities."""
        path = pathlib.Path(file_path)
        if not path.exists():
            print(f"[Warning] Training file '{file_path}' not found.")
            return

        print(f"Reading and training on '{file_path}'...")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        lines = text.replace("\r", "").split("\n")
        trained_count = 0

        for line in lines:
            tokens = line.lower().strip().split()
            if tokens:
                self.markov.train(tokens)
                trained_count += 1

        print(f"Training complete. Processed {trained_count} lines.")

    def talk(self) -> None:
        """Executes the interactive terminal session loop."""
        previous_response_tokens: List[str] = []

        try:
            while True:
                # Handle periodic auto-saving based on interaction turn count
                if self.auto_save:
                    self.session_count += 1
                    if self.session_count >= self.save_interval:
                        self.session_count = 0
                        self.storage.save(self.markov)

                raw_input = input("You: ").strip()

                # Process system control directives
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

                # Update model transitions using incoming user prompt
                self.markov.train(input_tokens)

                # Train cross-turn sequence mapping prior output to current input
                if previous_response_tokens:
                    self.markov.train(previous_response_tokens + input_tokens)

                # Generate response based on current context state
                answer = self.markov.generate(seed_tokens=input_tokens)
                print(f"Babbler: {answer}")

                self.tts.speak(answer)

                previous_response_tokens = answer.split()

        finally:
            self.storage.save(self.markov)


if __name__ == "__main__":
    bot = Babbler(corpus_file="corpus.txt", enable_tts=True, order=2)
    bot.talk()