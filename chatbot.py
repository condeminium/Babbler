import random, pickle, os
import os.path
help_message = """type #quit to quit"""
welcome_message = """Welcome to Babbler bot. This bot will learn from your input and will atempt to form responses via dictionary assosciation. A lot of it will be babbling but it will sometimes speak with coherence! (type #help for more commands or #quit to exit and save)
"""
class babbler():
    def __init__(self, save, delete_duplicates, count, maximum_words, maximum_responses):
        self.save = save
        self.count = count
        self.delete_duplicates = delete_duplicates
        self.maximum_words = maximum_words
        self.maximum_responses = maximum_responses
        self.memory = {}
        self.wordcount = 0
        self.session_count = 0
        os.system("cls")
        os.system("clear")
        print(welcome_message)
        if os.path.isfile("memory.data"): 
            self.memory = pickle.load(open('memory.data', "rb"))
            print("Memory file found")
        else:
            print("No memory file found.")
        print()
        for key, value in self.memory.items():
            self.wordcount += 1
    def question(self, x):
        self.wordcount += 1
        a = "w" + str(self.wordcount)
        d = {"name": x, "reply": [x], "uses": 0}
        self.memory[a] = d
    def talk(self):
        talking = True
        previous_response = ""
        while talking:
            if self.save:
                self.session_count += 1
                if self.session_count >= self.count:
                    self.session_count = 0
                    pickle.dump(self.memory, open('memory.data', 'wb'))
                    print("Saving...")
            if self.delete_duplicates:
                for key, value in self.memory.items():
                    value["reply"] = list(set(value["reply"]))
            if len(self.memory.keys()) > self.maximum_words:
                count = 0
                for key, value in self.memory.items():
                    count += value["uses"]
                for i in range(self.wordcount):
                    for key, value in self.memory.items():
                        if value["uses"] <= count/self.wordcount: 
                            self.wordcount -= 1
                            self.memory.pop(key, None)
                            break
            for key, value in self.memory.items():
                if len(value["reply"]) > self.maximum_responses:
                    rem = random.choice(value["reply"])
                    value["reply"].remove(rem)    
            answer = "" 
            a = input("You: ")
            if "#" in a:
                if "quit" in a:
                    pickle.dump(self.memory, open('memory.data', 'wb'))
                    print("Saving...")
                    exit()
                if "help" in a:
                    print(help_message)
                a = ""

            data = previous_response.split(" ")
            inp = a.split(" ")

            for x in data:
                for key, value in self.memory.items():
                    if x == value["name"]:
                        value["reply"].extend(inp)
            for x in inp:
                if a == "":
                    break
                names = []
                for key, value in self.memory.items():
                    names.append(value["name"])
                if x not in names:
                    self.question(x)
                else:
                    for key, value in self.memory.items():
                        if x == value["name"]:
                            xyz = random.randrange(0,4)
                            for i in range(xyz):
                                answer = answer + " {0}".format(random.choice(value["reply"]))
                                value["uses"] += 1
            if answer == "":
                answer = " ..."
            print("Babbler:{0}".format(answer))
            previous_response = answer
run = babbler(True, True, 25, 1000, 15)
run.talk()
