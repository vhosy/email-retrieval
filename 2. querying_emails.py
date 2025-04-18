"""
This script is for converting query into a text embedding and extracting all N
emails that are highly similar to the query from the email database
"""


from helper_functions import *
import ast
import pandas as pd

#load datasets if already ran earlier steps previously
df = pd.read_csv('data/df.csv')
df_long = pd.read_csv('data/df_long.csv')
df_long['embedding_values'] = df_long['embedding_values'].apply(lambda s: list(ast.literal_eval(s)))

#extract top N emails that are related to the query
see = find_email('which email by wei fong is about openai coding?', 5, df, df_long, advance_filter = "Y")
see = find_email('which is the email from kohei where he approved uat for lan wan ip extension?', 5, df, df_long, advance_filter = "Y")
see = find_email("martin's farewell", 5, df, df_long)


NER = get_NER(labels, 'which email by wei fong is about openai coding?')

# from langchain_openai import AzureOpenAIEmbeddings
# import os

# tiktoken_cache_dir = "C:/Users/P1345712/tiktoken_cache"
# os.environ["TIKTOKEN_CACHE_DIR"] = tiktoken_cache_dir
# os.environ["AZURE_OPENAI_API_KEY"] = os.getenv("AZURE_OPENAI_KEY")

# embeddings = AzureOpenAIEmbeddings(
#     azure_deployment="text_embedding-ada-002-default",
#     openai_api_version="2023-10-01-preview",
# )
# text = "This is a test query."
# query_result = embeddings.embed_query(text)
