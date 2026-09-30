========
Babbler
========
Babbler is a self learning markov style chatbot. It learns language patterns by associating words in user input with previous responses and saves them to a memory file stored on disk.

=========
Features
=========
Word assosciation

Memory Saving

Memory pruning

Text to speech (optional)

==========
Components
==========
Babbler consists of four primary components:

TTSHandler: Manages async audio output via pyttsx3. Creates new threads for audio generation so that text render is never blocked by TTS.

WordNode: Each node maintains a list of associated reply words and a counter to track frequency.

MemoryBank & StorageHandler: Handles state management and disk serialization (memory.data). Implements pruning based on word usage and maximum limits as described above.

Babbler: The main loop

============
Requirements
============
Python: 3.8+

Dependencies:

pyttsx3 (optional but required for TTS)


========
Commands
========

#help – Displays the command menu.

#tts  – Toggles text-to-speech on or off.

#quit – Saves current memory state to disk and exits.

=============
Configuration
=============
You can customize the Babbler instance parameters directly at the bottom of the file inside if __name__ == "__main__"::

Python
bot = Babbler(
    memory_file="memory.data",     # Filepath for saved memory
    auto_save=True,                # Enable periodic auto-saving
    save_interval=25,              # Auto-save frequency (in input turns)
    max_words=1000,                # Maximum unique word nodes to store
    max_responses_per_word=15,    # Association limit per word node
    deduplicate=True,              # Remove duplicate reply associations
    enable_tts=True                # Enable speech output on startup
)
bot.talk()

=======
License
=======
This project is open-source and available under the MIT License.