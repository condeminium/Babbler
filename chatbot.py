import os
import pickle
import random


class WordNode:
    """Encapsulates a single word's learned association data and statistics."""

    def __init__(self, name: str):
        self.name = name
        self.reply = [name]
        self.uses = 0

    def add_replies(self, words: list):
        self.reply.extend(words)

    def deduplicate(self):
        self.reply = list(set(self.reply))

    def prune_replies(self, max_responses: int):
        if len(self.reply) > max_responses:
            self.reply.remove(random.choice(self.reply))

    def generate_response(self) -> str:
        count = random.randrange(0, 4)
        selected_words = []
        for _ in range(count):
            if self.reply:
                selected_words.append(random.choice(self.reply))
                self.uses += 1
        return " ".join(selected_words)


class Babbler:
    HELP_MESSAGE = "type #quit to quit\n"
    WELCOME_MESSAGE = "Welcome to Babbler bot. Type #help for commands or #quit to exit.\n"

    def __init__(
        self,
        save: bool = True,
        delete_duplicates: bool = True,
        save_interval: int = 25,
        max_words: int = 1000,
        max_responses: int = 15,
    ):
        self.save_enabled = save
        self.delete_duplicates = delete_duplicates
        self.save_interval = save_interval
        self.max_words = max_words
        self.max_responses = max_responses

        self.memory: dict[str, WordNode] = {}
        self.session_count = 0

        os.system("cls" if os.name == "nt" else "clear")
        print(self.WELCOME_MESSAGE)
        self.load_memory()

    def load_memory(self):
        if os.path.isfile("memory.data"):
            try:
                with open("memory.data", "rb") as f:
                    self.memory = pickle.load(f)
                print("Memory file loaded successfully.")
            except Exception as e:
                print(f"Error loading memory: {e}")
        else:
            print("No memory file found. Initializing new memory bank.")

    def save_memory(self):
        try:
            with open("memory.data", "wb") as f:
                pickle.dump(self.memory, f)
            print("Saving memory...")
        except Exception as e:
            print(f"Error saving memory: {e}")

    def prune_memory(self):
        # Clean duplicate and over-capacity responses
        for node in self.memory.values():
            if self.delete_duplicates:
                node.deduplicate()
            node.prune_replies(self.max_responses)

        # Evict low-usage words if max memory size is exceeded
        if len(self.memory) > self.max_words:
            total_uses = sum(node.uses for node in self.memory.values())
            avg_uses = total_uses / len(self.memory) if self.memory else 0

            for key in list(self.memory.keys()):
                if len(self.memory) <= self.max_words:
                    break
                if self.memory[key].uses <= avg_uses:
                    del self.memory[key]

    def talk(self):
        previous_response_tokens = []

        while True:
            if self.save_enabled:
                self.session_count += 1
                if self.session_count >= self.save_interval:
                    self.session_count = 0
                    self.save_memory()

            self.prune_memory()

            raw_input = input("You: ").strip()

            if "#" in raw_input:
                if "quit" in raw_input:
                    self.save_memory()
                    break
                if "help" in raw_input:
                    print(self.HELP_MESSAGE)
                continue

            input_tokens = raw_input.split()
            if not input_tokens:
                continue

            # Update associations between previous output and current input
            for prev_token in previous_response_tokens:
                if prev_token in self.memory:
                    self.memory[prev_token].add_replies(input_tokens)

            # Learn new input words and generate responses
            response_tokens = []
            for word in input_tokens:
                if word not in self.memory:
                    self.memory[word] = WordNode(word)

                generated_chunk = self.memory[word].generate_response()
                if generated_chunk:
                    response_tokens.append(generated_chunk)

            answer = (
                " ".join(response_tokens) if response_tokens else "..."
            )
            print(f"Babbler: {answer}")
            previous_response_tokens = answer.split()


if __name__ == "__main__":
    bot = Babbler()
    bot.talk()