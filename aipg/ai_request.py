import json
import os
import pprint as pp
from typing import Union
import openai
from openai.openai_object import OpenAIObject
import tiktoken
from .logger import logger



pp.PrettyPrinter(indent=4, compact=False, width=100)
printf = pp.pformat

class Schema:
    def __init__(self, schema_config=None):
        if not schema_config:
            self.mlog = logger
            self.schema = \
            [
                {
                    "index": int,
                    "company": str,
                    "job_title": str,
                    "job_description": str,
                    "additional_info": str,
                    "num_tokens": int,
                    "response_generated": bool, 
                    "response_count": int,
                    "response_text": list,
                    "response_model": list,
                    "response_timestamp": list,
                    "response_cost": list,
                    "total_cost": int 
                    }
                ] 
        else:
            with open(schema_config, 'r') as schema_file:
                self.schema = json.load(schema_file)
    def validate_schema(self, case):
        """
        TODO:
            Write a schema validating function.
        """
        if isinstance(case, list):
            for item in case:
                if isinstance(item, dict):
                    for k, v in item.items():
                        try:
                            self.mlog.debug(f"\nk: {k}\nv: {v}")
                            type_check = isinstance(v, self.schema[0][k])
                        except KeyError as err:
                            self.mlog.warn(f"Key: {k} not found in schema:\n{err}")
                            return {"valid": False, "message": f"Validation failed with a KeyError for {k} in:\n{item}"}
                        if not type_check:
                            return {"valid": False, "message": f"Value type error for {k}: {v} in item:\n{item}"}
                else:
                    return {"valid": False, "message": f"All entries have to be a dictionaries:\n{item}"} 
        else:
            return {"valid": False, "message": f"Entries must be in the form List[dict]. The top level object passed is {type(case)}"}

        return {"valid": True, "message": "Looks like it's valid"}

class QueryData(list):
    def __init__(self, 
                 db_path:Union[str, os.PathLike],
                 schema_config:Union[str, os.PathLike, None]=None):
        self.db_path = db_path
        self.mlog = logger
        self.data = self._load_dataset(db_path)
        self._schema = Schema(schema_config)
        self.schema = Schema(schema_config).schema
        self.validate = self._schema.validate_schema

    def _load_dataset(self, file_path):
        """
        The purpose of this function is to import the dataset of all jobs data contained in the data
        folder.
        """
        if os.path.exists(file_path):
            print("test")
            self.mlog.info(f"Found a file at path: {file_path}")
            with open(file_path, "r") as db_file:
                data = json.load(db_file)
            return sorted(data, key=lambda x: x['index'])
        else:
            return []

    def add_entries(self, entries:Union[str, os.PathLike, list, None]=None):

        if isinstance(entries, str):
            entries = self._check_string(entries)
        if isinstance(entries, list):
            check = self.validate(entries)
        else:
            return

        if check['valid']:
            for item in entries:
                for k, v in self.schema[0].items():
                    item.setdefault(k, v())
            self.insert_entries(entries)
        else:
            self.mlog.warn(f"Data validation failed with message:\n{check}")
        return
            
            
    def _check_string(self, string):
        """
        check if an entry string is a valid json object or a valid path.

        return the object as a dict
        """
        if os.path.exists(string):
            with open(string, 'r') as file:
                data = json.load(file)
        else:
            try:
                data = json.loads(string)
            except ValueError as err:
                self.mlog.info(f"Entry string is not valid json:\n{err}")
                return
        return data

    def insert_entries(self, entries):
        idx_range = list(range(len(self.data)))
        entry_idx = list(range(len(self.data), len(self.data) + len(entries)))
        self.mlog.debug(f"entry indexes: {entry_idx}")
        self.mlog.info(f"New entry range {idx_range}.extend({entry_idx})")
        for idx, entry in zip(entry_idx, entries):
            if idx in idx_range:
                self.mlog.warning(f"Skipping: \n{entry}\nindex: {idx}\nFound entry index in self.data.")
                continue
            entry['index'] = idx
            self.data.append(entry)
        response = self.save_updates("add")
        self.mlog.info(f"message: {response['message']}")
            
    
    def update_entries(self, updates):
        """
        This function will recieve a report back from letter maker after each round of quieres and
        use that report to update the database.
        """
        for item in updates:
            if item['response_text'] == "Request Failed":
                continue
            self.mlog.debug(f"\nupdating entries for:\nitem['index']: {item['index']}")
            for k, v in item.items():
                self.mlog.debug(f"\ndata[item['index']]:\n{k} => {v}")
                if isinstance(self.data[item['index']][k], list):
                    self.data[item['index']][k].append(v)
                else:
                    self.data[item['index']][k] = v
            self.mlog.debug(f"self.data[idx]['response_cost']:\n{self.data[item['index']]['response_cost']}") 
            self.data[item['index']]['response_count'] = len(self.data[item['index']]['response_text'])
            self.data[item['index']]['total_cost'] = sum(self.data[item['index']]['response_cost'])

        response = self.save_updates("update")
        self.mlog.info(f"\nresponse: {response['message']}")

    def save_updates(self, request:str):
        try:
            with open(self.db_path, 'w') as db_file:
                json.dump(self.data, db_file, indent=4)
        except Exception as err: 
           self.mlog.exception(f"encountered exception while processing {request}:\n{err}")

        return {'message': f"{request} was successful"}
        
class LetterMaker:
    def __init__(self, 
                 data_dir:os.PathLike,
                 config_path:str='~/.openai', 
                 config_id:Union[int, None]=None):
        """
        config file:
            {
                key: zhkdks...,
                current_cost: 0,
                total_tokens: 0
                configs: [
                    index: 0,
                    token_count: 0,
                    pinfo: "personal info",
                    template: "Letter temples...",
                    system_message: "You are an expert in impressing people and doing business. You are a very helpful assistant.",
                    instructions: "I need you to help me get a job by writing a very nice cover-letter based on this template: ",
                    first_message: "Oh, I would love to do that. Can you please tell me about yourself?",
                    ],
                    ...
                    }
        """
        self.data_dir = data_dir
        self.data_obj = QueryData(self.data_dir)
        self.job_data = self.data_obj.data
        self.config_path = config_path
        self.config = self.load_config(config_id)
        self.mlog = logger

    def load_config(self, config_idx):
        """
        Load the config into memory. Use config index 0 if the index is not passed as
        an argument, or the passed index is out of bounds for the config list.
        """
        if config_idx is None:
            config_idx = 0
        with open(self.config_path, 'r') as confile:
            config_file = json.load(confile)
        try:
            config = config_file['configs'][config_idx]
        except IndexError:
            config = config_file['configs'][0]
            self.mlog.info("You past an invalid configuration id. Changing id value to 0.")
            self.mlog.warn(f"Configuration has {len(config_file)} entries. You attempted to get entry {config_idx}")
        config.update({'key': config_file['key']})
        return config

    def _transaction_record(self, response, index):
        """
        Constructor for a record to update the data-base.
        """
        cost = response['usage']['total_tokens'] * (.002 / 1000)
        update = {
                "index": index,
                "num_tokens" : response['usage']['total_tokens'],
                "response_model" : response['model'],
                "response_text" : response['choices'][0]['message']['content'],
                "response_timestamp": response['created'],
                "response_cost": cost,
                "response_generated": True
                }
        return update

    def _update_transaction_record(self, updates):
        """
        Update the config file with token and cost estimates from the transaction.
        """
        tokens_spent = sum([item['num_tokens'] for item in updates if item['num_tokens']])
        total_cost = tokens_spent * (.002 / 1000)

        self.mlog.debug(f"tokens in transaction:     {tokens_spent}")
        self.mlog.debug(f"cost of transaction:       {total_cost}")

        with open(self.config_path, "r") as cfile:
            config_file = json.load(cfile)
    
        config_file['total_tokens'] += tokens_spent
        config_file['current_cost'] += total_cost
        with open(self.config_path, 'w') as cfile:
            json.dump(config_file, cfile, indent=4)
        """
        Send the updates through to the data management object to record the responses into the 
        json file.
        """
        self.data_obj.update_entries(updates) 
        

    def make(self, new_only:bool=True, indexes:Union[list, None]=None):
        """
        Have gpt-3.5 make a cover letter.
        """ 
        import time
        if new_only:
            job_data = [item for item in self.job_data if not item['response_generated']]
        else:
            job_data = [item for item in self.job_data if item['index'] in indexes]
        if not job_data:
            return {"response": "Failed to find any job data"}

        update_list = []
        for job in job_data:
            self.mlog.debug(printf(f"starting query for:\ncompany: {job['company']}\nposition: {job['job_title']}"))
            job_query = f"Company: {job['company']}\nPosition Title: {job['job_title']}\ndescription: {job['job_description']}"
            response = self.query(job_query + job['additional_info'])
            start = time.time()
            sec = 1.0
            while not isinstance(response, OpenAIObject):
                if time.time() > start + sec:
                    print(sec)
                    print(f"current response: {type(response)}")
                    sec += 1.0
                

            #self.mlog.debug(f"RESPONSE:\n{response}")
            if isinstance(response, OpenAIObject):
                update_list.append(self._transaction_record(response, job['index']))
            else:
                update_list.append({
                                    "index": job['index'],
                                    "response_text": "Request Failed",
                                    "response_generated": False,
                                    })

        self._update_transaction_record(update_list)
        return {"response": "Successfully Created the cover letters"}

    def query(self, description):
        # query_len = [self.config['system_message'],
        #              self.config['instructions'],
        #              self.config['first_message'],
        #              self.config['pinfo'], 
        #              self.config['template'], 
        #              description]
        # encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        # total_tokens = 0
        # for x in query_len:
        #     total_tokens += len(encoding.encode(x))

        MODEL = "gpt-3.5-turbo"
        openai.api_key = self.config['key']
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.config['system_message']},
                {"role": "user", "content": self.config['instructions']},
                {"role": "assistant", "content": self.config['first_message']},
                {"role": "user", "content": "Here is my info: " + self.config['pinfo']},
                {"role": "assistant", "content": "Great! What job are you applying for?"},
                {"role": "user", "content": "This is the job listing: " + description},
                {"role": "assistant", "content": "Great! What letter template should use?"},
                {"role": "user", "content": "Here it is: " + self.config['template']},
            ],
            temperature=0,
        )
        return response

class OpenAIObject_Fake:
    def __init__(self):
        self.response = self.load_response()
        self.mlog = logger

    def load_response(self):
        with open("./data/fake_response.txt", "r") as fake:
            response = json.load(fake)
        return response

class TimedResponse:
    def __init__(self, duration:int=10):
        import time
        self.start = time.time()
        self.duration = duration
        self.mlog = logger

    def timer(self):
        import time
        t_plus = 1
        while time.time() < self.start + self.duration:
            if time.time() >= self.start + t_plus:
                self.mlog.debug(f"{t_plus}:\nresponse: {type(self)}")
                t_plus += 1
        return OpenAIObject_Fake()

