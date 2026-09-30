import os
import pickle
import random

HELP_MESSAGE = "type #quit to quit\n"
WELCOME_MESSAGE = """Welcome to Babbler bot. This bot will learn from your input and will attempt to form responses via dictionary association. A lot of it will be babbling, but it will sometimes speak with coherence! (type #help for more commands or #quit to exit and save)
"""


class Babbler:
    def __init__(
        self,
        save: bool,
        delete_duplicates: bool,
        count: int,
        maximum_words: int,
        maximum_responses: int,
    ):
        self.save = save
        self.count = count
        self.delete_duplicates = delete_duplicates
        self.maximum_words = maximum_words
        self.maximum_responses = maximum_responses
        self.memory = {}
        self.wordcount = 0
        self.session_count = 0

        # Cross-platform terminal clear
        os.system("cls" if os.name == "nt" else "clear")
        print(WELCOME_MESSAGE)

        if os.path.isfile("memory.data"):
            with open("memory.data", "rb") as f:
                self.memory = pickle.load(f)
            print("Memory file found.")
        else:
            print("No memory file found.")

        print()
        self.wordcount = len(self.memory)

    def question(self, x: str):
        self.wordcount += 1
        key = f"w{self.wordcount}"
        self.memory[key] = {"name": x, "reply": [x], "uses": 0}

    def talk(self):
        talking = True
        previous_response = ""

        while talking:
            # Auto-saving mechanism
            if self.save:
                self.session_count += 1
                if self.session_count >= self.count:
                    self.session_count = 0
                    with open("memory.data", "wb") as f:
                        pickle.dump(self.memory, f)
                    print("Saving...")

            # Remove duplicates from response
            if self.delete_duplicates:
                for value in self.memory.values():
                    value["reply"] = list(set(value["reply"]))

            # Dictionary pruning
            if len(self.memory) > self.maximum_words:
                total_uses = sum(
                    value["uses"] for value in self.memory.values()
                )
                avg_uses = total_uses / len(self.memory) if self.memory else 0

                # Iterate over static list of keys
                for key in list(self.memory.keys()):
                    if len(self.memory) <= self.maximum_words:
                        break
                    if self.memory[key]["uses"] <= avg_uses:
                        self.wordcount -= 1
                        del self.memory[key]

            # Max responses per word
            for value in self.memory.values():
                if len(value["reply"]) > self.maximum_responses:
                    rem = random.choice(value["reply"])
                    value["reply"].remove(rem)

            answer = ""
            a = input("You: ").strip()

            # Commands
            if "#" in a:
                if "quit" in a:
                    with open("memory.data", "wb") as f:
                        pickle.dump(self.memory, f)
                    print("Saving...")
                    break
                if "help" in a:
                    print(HELP_MESSAGE)
                a = ""

            if not a:
                continue

            data = previous_response.split()
            inp = a.split()

            # Extend previous words with new input words
            for x in data:
                for value in self.memory.values():
                    if x == value["name"]:
                        value["reply"].extend(inp)

            # Get user input and select responses
            for x in inp:
                names = [val["name"] for val in self.memory.values()]
                if x not in names:
                    self.question(x)
                else:
                    for value in self.memory.values():
                        if x == value["name"]:
                            xyz = random.randrange(0, 4)
                            for _ in range(xyz):
                                selected_reply = random.choice(value["reply"])
                                answer += f" {selected_reply}"
                                value["uses"] += 1

            if not answer.strip():
                answer = " ..."

            print(f"Babbler:{answer}")
            previous_response = answer


if __name__ == "__main__":
    run = Babbler(
        save=True,
        delete_duplicates=True,
        count=25,
        maximum_words=1000,
        maximum_responses=15,
    )
    run.talk()