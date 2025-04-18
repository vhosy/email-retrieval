"""
This script is to extract emails from outlook, structure the data into a pandas
dataframe and create text embedding of the email content
"""

from microsoft_graph_outlook import MSGraphOutlook
from helper_functions import *
import ast
import pandas as pd
import nltk

#initiate MS graph outlook API
graph = MSGraphOutlook()
graph_client = graph.start_graph_client()
graph_client.login()

#download all emails from outlook
email_content = graph.get_emails_all(graph_client)

#get only relevant information needed and put in a dataframe
email_content_processed = []

for i in range(len(email_content)):
    
    temp = graph.extract_email_info(email_content[i])
    email_content_processed.append(temp)
    
df = pd.DataFrame()
df['email_messages'] =  [x['message'] for x in email_content_processed ]
df['sender'] =  [x['sender_name'] for x in email_content_processed ]
df['sender_email'] =  [x['sender_email'] for x in email_content_processed ]
df['sent_date'] = [x['sent_date'] for x in email_content_processed ]
df['sent_date'] = pd.to_datetime(df['sent_date']).dt.date
df['subject'] =  [x['subject'] for x in email_content_processed ]
df['recipients'] =  [x['to_names'] for x in email_content_processed ]
df['recipients_email'] =  [x['to_email_address'] for x in email_content_processed ]
df['email_weblink'] = [x['email_weblink'] for x in email_content_processed ]


#testing, 
#test = df.head(100)
#test2 = df[~df['email_weblink'].isin(test['email_weblink'])]

#process the emails
df['email_messages'] = df['email_messages'].apply(lambda x : normalize_text(x))

# count number of words in emails and only keep emails that have >5 words
df['tokens'] = df['email_messages'].apply(lambda x :len(nltk.word_tokenize(x)))
df = df[(df['tokens']>5)]
df = df.sort_values(by=['tokens'])
df = df.reset_index()

# Chunk up the email messages into chunks of 4000 words
df['chunked'] = df['email_messages'].apply(chunk_string)
df['chunked'] = df['chunked'].apply(str).apply(ast.literal_eval)

#get the embeddings for the email messages
n_chunks = max(df['chunked'].apply(lambda x: len(x)))
embeddings = [[] for _ in range(n_chunks)]
embeddings_index = [[] for _ in range(n_chunks)]

for i in range(len(df)):
    for j in range(len(df['chunked'][i])):
       temp = generate_embeddings (df['chunked'][i][j])
       embeddings[j].append(temp)
       embeddings_index[j].append(i)

#merge all embeddings to dataframe
for i in range(n_chunks):
    temp =  pd.DataFrame(columns= ['embeddings_' + str(i)])
    temp['embeddings_' + str(i)] = embeddings[i]
    temp.index = embeddings_index[i]

    df = pd.merge(df, temp, how = 'left', left_index=True, right_index=True)
      
#get long format of dataframe
embedding_columns = df.filter(like='embedding').columns
df_long = pd.melt(df, id_vars = ['index','email_messages', 'sender', 'sender_email', 'sent_date', 'subject','recipients', 'recipients_email', 'email_weblink'],
                  value_vars = embedding_columns ,
                  var_name = 'embedding',
                  value_name = 'embedding_values'
                  )
df_long = df_long[~df_long['embedding_values'].isnull()]

#save datasets
df.to_csv('data/df.csv', index = False)
df_long.to_csv('data/df_long.csv', index = False)
  