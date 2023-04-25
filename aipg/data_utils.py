import os
import json
import logging
import pprint as pp
from pprint import pformat
import sys

import tiktoken

pp.PrettyPrinter(indent=4, width=1000, depth=5)

from ai_request import QueryData


encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
logging.basicConfig(level=logging.INFO)

def make_config(config_path, personal_info, template):
    with open(config_path, "r") as file:
        config = json.load(file)
    with open(personal_info, "r") as pfile:
        p_info = pfile.read()
    with open(template, 'r') as tfile:
        ltr_template = tfile.read()
    config['configs'][0]['pinfo'] = p_info
    config['configs'][0]['template'] = ltr_template
    tokens = []
    for k, v in config['configs'][0].items():
        if isinstance(v, str):
            logging.debug(f"(k, tokens(v)):\n{(k, len(encoding.encode(v)))}")
            tokens.append(len(encoding.encode(v)))
        else:
            continue
    logging.info(f"tokens: {tokens}")
    config['configs'][0]['token_count'] = sum(tokens) 
    with open(config_path, "w") as cfile:
        json.dump(config, cfile, indent=2)
     

make_config("/home/drew/.openai-key", "./data/info.txt", "./data/template.txt")
    
