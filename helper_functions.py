"""
This script contains all functions for processing email contents, doing text 
embedding and searching up relevant emails from the database based on query
given
"""


import ast
import re
import jellyfish
import json
import nltk
import numpy as np
import os
import pandas as pd
from openai import AzureOpenAI
from datetime import datetime

client = AzureOpenAI(
  azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT"), 
  api_key=os.getenv("AZURE_OPENAI_KEY"),  
  api_version="2023-05-15"
)

start_string = '________________________________________________________________________________'
end_string = '________________________________________________________________________________'

labels = [
    "person",      # people, including fictional characters
    "fac",         # buildings, airports, highways, bridges
    "org",         # organizations, companies, agencies, institutions
    "gpe",         # geopolitical entities like countries, cities, states
    "loc",         # non-gpe locations
    "product",     # vehicles, foods, appareal, appliances, software, toys 
    "event",       # named sports, scientific milestones, historical events
    "work_of_art", # titles of books, songs, movies
    "law",         # named laws, acts, or legislations
    "language",    # any named language
    "date",        # absolute or relative dates or periods
    "time",        # time units smaller than a day
    "percent",     # percentage (e.g., "twenty percent", "18%")
    "money",       # monetary values, including unit
    "quantity",    # measurements, e.g., weight or distance
]

def remove_cid_image(text):
    """
       removes all 'cid:image ...' and 'data:image ...' links

       Args:
           text (str): text to search for 'cid:image ...'

       Raises:
           TypeError: If 'text' is not a string
           
       Returns:
           str: the text with 'cid:image ...' removed

       Examples:
           >>> remove_cid_image("This is a sample (cid:image123) string with 
                                (data:imagex456) some occurrences.")
           returns "This is a sample string with some occurrences"

       """
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
            
    pattern = re.compile(r'\(cid:image.*?\)')
    result_string = re.sub(pattern, '', text)
    pattern = re.compile(r'\(data:image.*?\)')
    result_string = re.sub(pattern, '', result_string)
    return result_string

def remove_http(text):
    """
       removes all 'http' links

       Args:
           text (str): text to search for 'http'

       Raises:
           TypeError: If 'text' is not a string
           
       Returns:
           str: the text with 'http' removed

       Examples:
           >>> remove_cid_image("This is a sample (https://www.singtel.com/) string with 
                                (https://www.starhub.com/) some occurrences.")
           returns "This is a sample string with some occurrences"

       """
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
            
    pattern = re.compile(r'\(http.*?\)')
    result_string = re.sub(pattern, '', text)
    return result_string

def remove_between_strings(input_string, start_string, end_string):
    """
       removes all text between a given start_string and end_string

       Args:
           input_string (str): the text which have the components needed to be 
           removed
           start_string (str): the pattern of the start_string
           end_string (str): the pattern of the end_string

       Raises:
           TypeError: If 'input_string', 'start_string', 'end_string' is not a string
           
       Returns:
           str: the text with all string between the given start_string and end_string removed

       Examples:
           >>> remove_between_strings("This is a sample string [hello]", '[', ']')
           returns "This is a sample string"

       """
    if not isinstance(input_string, str):
        raise TypeError ('input_string needs to be a string')
    
    if not isinstance(start_string, str):
        raise TypeError ('start_string needs to be a string') 
    
    if not isinstance(end_string, str):
        raise TypeError ('end_string needs to be a string')
        
    pattern = re.compile(re.escape(start_string) + '.*?' + re.escape(end_string), re.DOTALL)
    result_string = re.sub(pattern, '', input_string)
    return result_string

# s is input text
def normalize_text(s, sep_token = " \n "):
    """
       text processing

       Args:
           s (str): the text to be processed

       Raises:
           TypeError: If 's' is not a string
           
       Returns:
           str: the text processed

       """
    if not isinstance(s, str):
        raise TypeError ('s needs to be a string')
        
    s = re.sub(r'\s+',  ' ', s).strip()
    s = re.sub(r". ,","",s)
    # remove all instances of multiple spaces
    s = s.replace("..",".")
    s = s.replace(". .",".")
    s = s.replace("\n", "")
    s = s.replace("*", "")
    s = remove_cid_image(s)
    s = remove_http(s)
    s = s.replace('**[CAUTION: External email]** Do not click links or open attachments unless you recognize the sender and know the content is safe.', '')
    s = remove_between_strings(s, '[', ']')
    s = remove_between_strings(s, '<', '>')
    s = s.replace(">", "")
    s = remove_between_strings(s, start_string, end_string) 
    s = s.strip()
    
    return s

def generate_embeddings(text, model='text_embedding-ada-002-default'): # model = "deployment_name"
    """
     generate text embedding

     Args:
         text (str): the text to be embedded
         model (str): the OpenAI model to be used for the text embedding

     Raises:
         TypeError: If 'text' is not a string
         
     Returns:
         list: the list of embeddings

     """
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
    return client.embeddings.create(input = [text], model=model).data[0].embedding

def chunk_string(text, max_words=4000):
    """
     cut up the text into chunks of specified number of words

     Args:
         text (str): the text to be chunked
         max_words (int): the maximum number of words in each chunk

     Raises:
         TypeError: If 'text' is not a string
         
     Returns:
         list: the list of chunked strings

     """
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
    words = nltk.word_tokenize(text)
    chunks = []
    current_chunk = []

    for word in words:
        if len(current_chunk + [word]) <= max_words:
            current_chunk.append(word)
        else:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]

    chunks.append(' '.join(current_chunk))
    return chunks

def cosine(u, v):
    """
     calculate the cosine similarity between 2 list of floats

     Args:
         u, v (list): the list of floats 

     Raises:
         TypeError: If u, v are not list
         
     Returns:
         list: the list of chunked strings

     """
    if not isinstance(u, list):
        raise TypeError ('u needs to be a list')
    if not isinstance(v, list):
        raise TypeError ('v needs to be a list')
        
    return np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v))


def system_message(labels):
    """
     generates the system message for chatgpt

     Args:
         labels (list): the list of NER
         
     Returns:
         str: system message

     """
    return f"""
You are an expert in Natural Language Processing. Your task is to identify common Named Entities (NER) in a given text.
The possible common Named Entities (NER) types are exclusively: ({", ".join(labels)})."""

def assisstant_message():
    """
     generates the assistant message for chatgpt
         
     Returns:
         str: assistant message

     """
     
    return f"""
EXAMPLE:
    Text: 'In Germany, in 1440, goldsmith Johannes Gutenberg invented the movable-type printing press. His work led to an information revolution and the unprecedented mass-spread / 
    of literature throughout Europe. Modelled on the design of the existing screw presses, a single Renaissance movable-type printing press could produce up to 3,600 pages per workday.'
    {{
        "gpe": ["Germany", "Europe"],
        "date": ["1440"],
        "person": ["Johannes Gutenberg"],
        "product": ["movable-type printing press"],
        "event": ["Renaissance"],
        "quantity": ["3,600 pages"],
        "time": ["workday"]
    }}
"""
def user_message(text):
    """
     generates the user message for chatgpt

     Args:
         text (list): the prompt to chatgpt
         
     Returns:
         str: user message

     """
    return f"""
TASK:
    Text: {text}
"""

def get_NER(labels, text):
    """
     generates NER of a prompt

     Args:
         labels (list): the list of NER
         text (list): the prompt to chatgpt
         
     Raises:
         TypeError: It 'label' is not list, If 'text' is not a string
          
     Returns:
         str: user message
   
     """
    if not isinstance(labels, list):
        raise TypeError ('labels needs to be a list')    
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
        
    messages = [
          {"role": "system", "content": system_message(labels=labels)},
          {"role": "assistant", "content": assisstant_message()},
          {"role": "user", "content": user_message(text=text)}
      ]

    response = client.chat.completions.create(
        model="gpt-35-turbo-16k-0613-vanilla",
        messages=messages,

        temperature=0,
        frequency_penalty=0,
        presence_penalty=0,
    )

    response_message = json.loads(response.choices[0].message.content)
    
    return response_message

def check_preceding_word(text, target_phrase):
    """
     get the preceding prepositions before the target phrase

     Args:
         text (str): the prompt to chatgpt
         target_phrase (str): the phrase to check the preceding word of
     Raises:
         TypeError: If 'text' or 'target_phrase' is not a string
          
     Returns:
         str: preceding preposition if any
   
     """
    if not isinstance(text, str):
        raise TypeError ('text needs to be a string')
    if not isinstance(target_phrase, str):
        raise TypeError ('target phrase to be a string')    
        
    pattern = re.compile(r'\b(?:from|to|by|in|within)\s+' + re.escape(target_phrase) + r'\b', re.IGNORECASE)
    matching = re.search(pattern, text)
    
    if matching is None:
        return ''   
    if 'from' in matching.group():
        return 'from'
    elif 'to' in matching.group():
        return 'to'
    elif 'by' in matching.group():
        return 'by'
    elif 'in' in matching.group():
        return 'in'
    elif 'within' in matching.group():
        return 'within'


def find_person (df_long, query, person_name):
    """
     filter for all rows in dataframe where the recipient/sender is in the 
     query text

     Args:
         df_long (dataframe): dataframe of emails in long format
         query (str): the prompt to chatgpt
         person_name (list): the list of person's names
     Raises:
         TypeError: If 'df_long' is not pandas dataframe, If 'query' is not a 
         string, If 'person_name' is not list
          
     Returns:
         dataframe: dataframe of only records from particular recipient/sender
   
     """
    if not isinstance(df_long, pd.DataFrame):
        raise TypeError ('df_long needs to be a pandas dataframe')
    if not isinstance(query, str):
        raise TypeError ('query needs to be a string')
    if not isinstance(person_name, list):
        raise TypeError ('person_name needs to be a list')        
        
    for name in person_name:
        
        direction = check_preceding_word(query, name)
        if direction in ['by', 'from']:     
            person = pd.DataFrame(df_long['sender'].drop_duplicates())
            person['similarity'] = person['sender'].apply(lambda x: jellyfish.jaro_distance(name, x))
            target = person.loc[person['similarity']==max(person['similarity']), 'sender'].values[0]
            df_long = df_long[df_long['sender'] == target]
            
        elif direction == 'to':
            person = pd.DataFrame(df_long['recipients'].apply(lambda s: list(ast.literal_eval(s))).explode().apply(str).drop_duplicates())
            person['similarity'] = person['recipients'].apply(lambda x: jellyfish.jaro_distance(name, x))
            target = person.loc[person['similarity']==max(person['similarity']), 'recipients'].values[0]
            df_long = df_long[df_long['recipients'].apply(lambda x: target in x)]
        
    return df_long
        
def find_org (df_long, query, org_name):
    """
     filter for all rows in dataframe where the recipient's/sender's organisation 
     is in the query text

     Args:
         df_long (dataframe): dataframe of emails in long format
         query (str): the prompt to chatgpt
         org_name (list): the list of organisation's names
     Raises:
         TypeError: If 'df_long' is not pandas dataframe, If 'query' is not a 
         string, If 'org_name' is not list
          
     Returns:
         dataframe: dataframe of only records from particular recipient/sender
         organisation
   
     """
    if not isinstance(df_long, pd.DataFrame):
        raise TypeError ('df_long needs to be a pandas dataframe')
    if not isinstance(query, str):
        raise TypeError ('query needs to be a string')
    if not isinstance(org_name, list):
        raise TypeError ('org_name needs to be a list')     
    
    for name in org_name:
        
        direction = check_preceding_word(query, name)
        if direction in ['by', 'from']:     
            temp = pd.DataFrame(df_long['sender_email'].drop_duplicates())
            temp['similarity'] = temp['sender_email'].apply(lambda x: jellyfish.jaro_distance(name, x))
            target = temp.loc[temp['similarity']==max(temp['similarity']), 'sender_email'].values[0]
            df_long = df_long[df_long['sender_email'] == target]
            
        elif direction == 'to':
            temp = pd.DataFrame(df_long['recipients_email'].apply(lambda s: list(ast.literal_eval(s))).explode().apply(str).drop_duplicates())
            temp['similarity'] = temp['recipients_email'].apply(lambda x: jellyfish.jaro_distance(name, x))
            target = temp.loc[temp['similarity']==max(temp['similarity']), 'recipients_email'].values[0]
            df_long = df_long[df_long['recipients_email'].apply(lambda x: target in x)]
        
    return df_long    
   
def find_date (df_long, query, date_list):
    """
     filter for all rows in dataframe where date is in the 
     query text

     Args:
         df_long (dataframe): dataframe of emails in long format
         query (str): the prompt to chatgpt
         date_list (list): the list of dates
     Raises:
         TypeError: If 'df_long' is not pandas dataframe, If 'query' is not a 
         string, If 'date_list' is not list
          
     Returns:
         dataframe: dataframe of only records in particular dates
   
     """
    if not isinstance(df_long, pd.DataFrame):
        raise TypeError ('df_long needs to be a pandas dataframe')
    if not isinstance(query, str):
        raise TypeError ('query needs to be a string')
    if not isinstance(date_list, list):
        raise TypeError ('date_list needs to be a list')         
    
    df_long['sent_date'] = pd.to_datetime(df_long['sent_date']).dt.date
    query = query.replace("/"," ")
    
    for date in date_list:
        date = date.replace("/"," ")
        target = pd.to_datetime(date)
        target = target.date()
        direction = check_preceding_word(query, date)
        if direction == 'from':     
            df_long = df_long[df_long['sent_date'] >= target]
            
        elif direction == 'to':
            if (target.month == 1) & (target.day == 1):
                df_long = df_long[df_long['sent_date'] <= datetime(target.year, 12, 31).date()]
            elif target.day == 1:
                df_long = df_long[df_long['sent_date'] <= datetime(target.year,  target.month, 31).date()]
            else:                
                df_long = df_long[df_long['sent_date'] <= target]
                
        elif direction in ['in', 'within']:
            if (target.month == 1) & (target.day == 1):
                df_long = df_long[pd.DatetimeIndex(df_long['sent_date']).year == target.year]
            elif target.day == 1:
                df_long = df_long[(pd.DatetimeIndex(df_long['sent_date']).year == target.year) &
                                  (pd.DatetimeIndex(df_long['sent_date']).month == target.month)]
                
            
            
    
    return df_long    

def find_email (query, top_n, df, df_long, advance_filter = 'N'):
    """
     filter for all rows in dataframe which fits the prompt query

     Args:
         query (str): the prompt to chatgpt
         top_n (int): top N rows of datarframe to filter
         df (dataframe):  dataframe of emails
         df_long (dataframe): dataframe of emails in long format
         person_name (list): the list of person's names
         advance_filter (str): whether to use advance filtering
     Raises:
         TypeError: If 'df' or 'df_long' is not pandas dataframe, If 'query' or 
         'advance_filter' is not a string, If 'top_n' is not integer
          
     Returns:
         dataframe: dataframe of only records that answers prompt query
   
     """
    if not isinstance(df_long, pd.DataFrame):
        raise TypeError ('df_long needs to be a pandas dataframe')
    if not isinstance(df, pd.DataFrame):
        raise TypeError ('df needs to be a pandas dataframe')    
    if not isinstance(query, str):
        raise TypeError ('query needs to be a string')
    if not isinstance(top_n, int):
        raise TypeError ('top_n needs to be an int')
    if not isinstance(advance_filter, str):
        raise TypeError ('advance_filter needs to be a str')
        
    embedding = generate_embeddings(
            query,
            model='text_embedding-ada-002-default' 
        )
    
    NER = get_NER(labels, query)
    if advance_filter != 'N':
        if 'person' in NER:
            df_long = find_person (df_long, query, NER['person'])
        
        if 'org' in NER:
            df_long = find_org (df_long, query, NER['org'])
        
        if 'date' in NER:
            df_long = find_date (df_long, query, NER['date'])
    
     
    df_long['similarities'] = [cosine(embedding,x) for x in df_long['embedding_values']]
    df_long = df_long.sort_values(by=['similarities'], ascending = False)
    ids = df_long[['index', 'similarities']].head(top_n)

    final = pd.merge(ids, df, how = 'left', on = 'index')
    final = final.sort_values(by=['similarities'], ascending = False)
    final = final[['email_messages','sender','sender_email', 
                   'sent_date', 'subject','recipients',
                   'recipients_email', 'email_weblink']]
    final['email_weblink'] = final['email_weblink'].apply(lambda x:  f'<a href="{x}">link</a>')
    
    return final