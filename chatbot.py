import random, pickle, os
import os.path
startmes = """Welcome Message
"""
class chatter():
    def __init__(self, save, delete_duplicates, count, maximum_words, maximum_responses):
        self.save = save
        self.count = count
        self.delete_duplicates = delete_duplicates
        self.maximum_words = maximum_words
        self.maximum_responses = maximum_responses
        self.memory = {}
        self.wordcount = 0
        self.sescount = 0
        os.system("cls")
        print(startmes)
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
        d = {"name": x, "resp": [x], "uses": 0}
        self.memory[a] = d
    def talk(self):
        talking = True
        prevres = ""
        while talking:
            if self.save:
                self.sescount += 1
                if self.sescount >= self.count:
                    self.sescount = 0
                    pickle.dump(self.memory, open('memory.data', 'wb'))
                    print("Saving...")
            if self.delete_duplicates:
                for key, value in self.memory.items():
                    value["resp"] = list(set(value["resp"]))
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
                if len(value["resp"]) > self.maximum_responses:
                    rem = random.choice(value["resp"])
                    value["resp"].remove(rem)    
            res = "" 
            a = input("You: ")
            if "#" in a:
                if "quit" in a:
                    pickle.dump(self.memory, open('memory.data', 'wb'))
                    print("Saving...")
                    exit()
                if "help" in a:
                    print(helpmes)
                a = ""

            data = prevres.split(" ")
            inp = a.split(" ")

            for x in data:
                for key, value in self.memory.items():
                    if x == value["name"]:
                        value["resp"].extend(inp)
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
                                res = res + " {0}".format(random.choice(value["resp"]))
                                value["uses"] += 1
            if res == "":
                res = " ..."
            print("chatter:{0}".format(res))
            prevres = res
sauce = chatter(True, True, 25, 1000, 15)
sauce.talk()
