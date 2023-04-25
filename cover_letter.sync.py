# %%
import os
import json
import openai
import tiktoken
from aipg.ai_request import LetterMaker

# %%
# %load_ext autoreload
# %autoreload 2

# %%
# %aimport aipg

# %%
dataguy = QueryData("./data/job_data.json")
dataguy

# %%
with open("./data/santander.txt", "r") as file:
    job = file.read() 

# %%
new_entry = {
    "company": "Santander Bank",
    "job_title": "Associate Data Science",
    "job_description": job
}
updates = [new_entry]

# %%
dataguy.add_entries(updates)

# %%
encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

# %%
lm = LetterMaker('./data/job_data.json', '/home/drew/.openai-key')

# %%
with open("/home/drew/.openai", "r") as cfile:
    config = json.load(cfile)

# %%
with open("/home/drew/.openai_backup", "w") as cfile:
    json.dump(config, cfile, indent=4)

# %%
lm.make(new_only=False, indexes=[0, 1])

# %%
import time
start_time = time.time()
sec = 1.0
while sec < 10.0:
    if time.time() > start_time + sec:
        print(time.time())
        sec += 1.0

# %%
from aipg.ai_request import TimedResponse, OpenAIObject_Fake

# %%
a = TimedResponse(5)
isinstance(a.timer(), OpenAIObject_Fake)
