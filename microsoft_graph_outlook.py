# -*- coding: utf-8 -*-
"""
This module provides functions for filtering out email messages, processing the
messages and getting the attachments through Microsoft Graph API. 

Classes:
    MSGraphOutlook
"""
import base64
import yaml
from datetime import datetime
from itertools import chain
import os
import html2text
import re
from ms_graph.client_GBNOC import MicrosoftGraphClient

class MSGraphOutlook (object):
    
    """
    A class for filtering out email messages, processing the messages and 
    getting the attachments through Microsoft Graph API. 
    """
    
    def start_graph_client (self) -> None:        
        """
        Starts up the Microsoft Graph client.

        Args:
            None

        Returns:
            None

        """

        proxy = 'http://singtelproxy.net.vic:80'

        os.environ['http_proxy'] = proxy 
        os.environ['HTTP_PROXY'] = proxy
        os.environ['https_proxy'] = proxy
        os.environ['HTTPS_PROXY'] = proxy

        # Load the oauth_settings.yml file
        stream = open('configs/oauth_settings.yml', 'r')
        config = yaml.load(stream, yaml.SafeLoader)

        # Get the specified credentials.
        client_id = config['app_id']
        client_secret = config['app_secret']
        redirect_uri = config['redirect']
        scopes = config['scopes']
        
        graph_client = MicrosoftGraphClient(client_id=client_id,
                                            client_secret=client_secret,
                                            redirect_uri=redirect_uri,
                                            scope=scopes,
                                            credentials="configs/ms_graph_state.jsonc")
        
        return graph_client
    
    def get_child_folder_id(self, graph_client, target_folder : str, main_folder = 'inbox'):
        """
        Gets the folder id of a named subfolder.

        Args:
            graph_client (obj): microsoft graph client object
            target_folder (str): The name of the child folder to get the 
            folder id of
            main_folder (str): The name of the parent folder, default is inbox

        Raises:
            TypeError: If 'target_folder' or 'main_folder' is not a string
            ValueError: If the 'target_folder' cannot be found

        Returns:
            str: the child folder id

        Examples:
            >>> get_child_folder_id(graph_client, 'Instant Quote')
            returns the folder ID of 'Instant Quote' which is a subfolder of
            Inbox

        """
        
        if not isinstance(main_folder, str):
            raise TypeError ('Folder id needs to be a string')
        
        if not isinstance(target_folder, str):
            raise TypeError ('Target folder name needs to be a string')    
        

        childfolders = graph_client.graph_session.make_request(method='get',
                                                               endpoint='/me/mailFolders/{0}/childFolders'.format(main_folder))
        
        childfolders_names = [x['displayName'] for x in childfolders[1]['value']]

        try:
            target_folder_id = childfolders[1]['value'][childfolders_names.index(target_folder)]['id']
            return target_folder_id
        except ValueError:
            print (f'No subfolder with name "{target_folder}" found')
 
    
    def get_emails (self, graph_client, subject = None, start_date = None, 
                    end_date = None, sender = None, folder_id = None, 
                    top_n = None) -> list:
        """
        Gets the required email(s) based on the filter requirement. Default 
        extracts top 10 latest emails across all folders, including deleted items.

        Args:
            graph_client (obj): microsoft graph client object
            subject (str): email subject
            start_date (str): email start received date in yyyy-mm-dd format
            end_date (str): email end received date in yyyy-mm-dd format
            sender (str): sender email address
            folder_id (str): email folder id
            top_n: number of N latest emails to extract

        Raises:
            TypeError: If 'subject', 'date', 'sender' or 'folder_id' is not a 
            string.  If 'top_n' is not an integer.
            
        Returns:
            list: list containing email attributes

        Examples:
            >>> get_emails(graph_client, 
                           folder_id = get_child_folder_id(graph_client, 
                                                           'Instant Quote'), 
                           sender = 'kyamamoto@singtel.com', 
                           start_date = '2022-08-25',
                           end_date = '2022-08-25')
            returns all emails in Instant Quote folder, sent by kyamamoto@singtel.com
            on 2022-08-25

        """
        
        filter_query = ''
        
        if subject is not None:
            #check if subject is a string
            if not isinstance(subject, str):
                raise TypeError ('Email subject needs to be a string')
            else:
                filter_query = filter_query + f"subject%20eq%20%27{subject}%27"
        
        if start_date is not None:
            #check if date is a string
            if not isinstance(start_date, str):
                raise TypeError ('Email start received date needs to be a date')
            else:
                start_date  = start_date  + 'T00:00:00Z'
                #if filter query is not empty, add an 'and' expression to the join
                if filter_query == '':
                    filter_query = filter_query + f'receivedDateTime%20ge%20{start_date}'
                else:
                    filter_query = filter_query + f'%20and%20receivedDateTime%20ge%20{start_date}'
        
        if end_date is not None:
            #check if date is a string
            if not isinstance(end_date, str):
                raise TypeError ('Email end received date needs to be a date')
            else:
                end_date = end_date + 'T23:59:59Z'
                #if filter query is not empty, add an 'and' expression to the join
                if filter_query == '':
                    filter_query = filter_query + f'receivedDateTime%20le%20{end_date}'
                else:
                    filter_query = filter_query + f'%20and%20receivedDateTime%20le%20{end_date}'
                    
        if sender is not None:
            #check if sender is a string 
            if not isinstance(sender, str):
                raise TypeError ('Email sender needs to be a string')
            else:
                #if filter query is not empty, add an 'and' expression to the join
                if filter_query == '':
                    filter_query = filter_query + f'sender/emailAddress/address%20eq%20%27{sender}%27'
                else:
                    filter_query = filter_query + f'%20and%20sender/emailAddress/address%20eq%20%27{sender}%27'
        
        if top_n is not None:
            #check if top_n is an integer
            if not isinstance(top_n, int):
                raise TypeError ('top N needs to be an integer')
            else:
                filter_query = filter_query + f'&%24top={top_n}'
        
        if folder_id is not None:
            #check if sender is a string 
            if not isinstance(folder_id, str):
                raise TypeError ('Email folder id needs to be a string')
            else:
                content = graph_client.graph_session.make_request(method='get',
                                                                  endpoint='/me/mailFolders/{0}/messages?$filter={1}'\
                                                                      .format(folder_id, filter_query))
        else:
            content = graph_client.graph_session.make_request(method='get',
                                                              endpoint='/me/messages?$filter={0}'\
                                                                  .format(filter_query))
        
        email_content = content[1]['value']
        
        return email_content 
    
    def extract_email_info(self, email_content : dict) -> dict:
        
        """
        Extract and process the email information

        Args:
            email_content (dict): dictionary of the raw email attributes 

        Raises:
            TypeError: If 'email_content' is not a dict.
            
        Returns:
            dict: dictionary containing processed email attributes

        Examples:
            >>> extract_email_info(email_content[0])
            returns processed email attributes for first email dictionary in 
            list of email_content

        """
        
        if not isinstance(email_content, dict):
            #check if email_content is dict
            raise TypeError ('Email content needs to be a dict')  
        
        #create empty dict and store processed email info
        email_info = {}
        
        message = email_content['body']['content'] 
        
        urls = re.findall(r'(https?://\S+)', message)
        urls = [value for value in urls if 'sharepoint' in value]

        email_info['message'] = html2text.html2text(message)     
        email_info['url'] = urls
        
        if 'sender' in email_content:
            email_info['sender_name'] = email_content['sender']['emailAddress']['name']
            email_info['sender_email'] = email_content['sender']['emailAddress']['address']
        else:
            email_info['sender_name'] = []
            email_info['sender_email'] = []
            
    
        email_info['sent_date']  = email_content['sentDateTime']
        email_info['subject'] = email_content['subject']

        email_info['to_names'] = [x['emailAddress']['name'] for x in email_content['toRecipients']]
        email_info['to_email_address'] = [x['emailAddress']['address'] for x in email_content['toRecipients']]

        email_info['cc_names'] = [x['emailAddress']['name'] for x in email_content['ccRecipients']]
        email_info['cc_email_address']= [x['emailAddress']['address'] for x in email_content['ccRecipients']]
        email_info['email_weblink'] =  email_content['webLink']
        
        return email_info
        
    def get_attachments(self, graph_client, email_content : dict, 
                        directory : str) -> None:
        
        """
        Find and download all attachments in email

        Args:
            graph_client (obj): microsoft graph client object
            email_content (dict): dictionary of the raw email attributes 
            directory (str): directory to store the attachments

        Raises:
            TypeError: If 'email_content' is not a dict.
            
        Returns:
            None

        Examples:
            >>> get_attachments(graph_client, email_content[0], 'test') 
            downloads all attachments in first email dictionary in to test folder

        """
    
        if not isinstance(email_content, dict):
            #check if email_content is a dictionary
            raise TypeError ('Email content needs to be a dict')       
    
        #if email has attachment, download and save to given directory specified
        if email_content['hasAttachments'] == False:
            print('Email has no attachments')
        else:
            if not os.path.exists(directory):
                print(f'"{directory}" does not exist, creating folder now')
                os.makedirs(directory)
            
            attachments = graph_client.graph_session.make_request(method='get',endpoint='/me/messages/{0}/attachments'.format(email_content['id']))
            attachment_id = [x['id'] for x in attachments[1]['value']]
            attachment_name = [x['name'] for x in attachments[1]['value']]

            for i in range(len(attachment_id)):
                graph_client.graph_session.make_request(method='get',
                                                    endpoint='/me/messages/{0}/attachments/{1}/$value'.format(email_content['id'], attachment_id[i] ), 
                                                    download = True,  
                                                    download_path = f"{directory}/{attachment_name[i]}")
                print(f'Downloaded {attachment_name[i]} to {directory}')
    
    
    def send_email (self, graph_client, subject: str, message: str, 
                    to_address: str, attachment_paths = None) -> None:
        
        """
        Send email based on given information

        Args:
            graph_client (obj): microsoft graph client object
            subject (str): email title
            message (str): email message content
            to_address (str): the email address to send the email to
            attachment_paths (list): optional, list of paths of the attachments
            to be sent

        Raises:
            TypeError: If 'subject', 'message' or 'to_address' is not a dict.
            If 'attachment_paths' is not a list
            
        Returns:
            None

        Examples:
            >>> send_email(graph_client, 'test', 'this is a test email', 
                           'shaoying.choo@gmail.com', ['test/image001.jpg']) 
            sends an email titled 'test' with imaged attached to 
            'shaoying.choo@gmail.com'

        """
        if not isinstance(subject, str):
            raise TypeError ('Subject needs to be a string')
        
        if not isinstance(message, str):
            raise TypeError ('Message needs to be a string')    
                    
        if not isinstance(to_address, str):
            raise TypeError ('To address needs to be a string')      
        
        #create the email structure
        email_payload = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": message,
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_address,
                        }
                    }
                ],
             "attachments": [],
            },
            "saveToSentItems": "true",
        }
        
        if attachment_paths is not None:
            
            if not isinstance(attachment_paths, list):
                raise TypeError ('attachment paths needs to be in a list')
                
            for attachment_path in attachment_paths:
                with open(attachment_path, "rb") as file:
                    content_bytes = file.read()
                
                base64_content = base64.b64encode(content_bytes).decode("utf-8")
                attachment = {
                        "@odata.type": "#microsoft.graph.fileAttachment",
                        "name": attachment_path.split("/")[-1],
                        "contentBytes": base64_content,
                    }
                email_payload["message"]["attachments"].append(attachment)
        
        graph_client.graph_session.make_request(method='post',
                                                endpoint = "/me/sendMail", 
                                                json = email_payload)
    
    def count_emails (self, graph_client, folder_id = None) -> int:
        
        """
        Counts the number of emails in outlook by default, else the number of 
        emails in specific folder id

        Args:
            graph_client (obj): microsoft graph client object
            folder_id (str): email folder id

        Raises:
            TypeError: If 'email folder id' is not a string.
            
        Returns:
            integer

        Examples:
            >>> count_emails(graph_client, get_child_folder_id(graph_client, 
                                            'Instant Quote')) 
            counts the number of emails in 'Instant Quote' folder in outlook

        """
        
        if folder_id is None:
            content =graph_client.graph_session.make_request(method='get',
                                        endpoint='/me/messages?$count=true')

        else:
            if not isinstance(folder_id, str):
                raise TypeError ('Email folder id needs to be a string')
            else:
                content = graph_client.graph_session.make_request(method='get',
                        endpoint='/me/mailFolders/{0}/messages?$count=true'
                        .format(folder_id))
        

        return content[1]['@odata.count']
    
    def get_emails_all (self, graph_client) -> list:
        
        """
        Get all emails in outlook

        Args:
            graph_client (obj): microsoft graph client object
            
        Returns:
            list

        Examples:
            >>> get_emails_all(graph_client)
            gets all emails in outlook

        """
        
        total_count = self.count_emails(graph_client)
        
        batch_size = 500
        
        content = []
        
        for skip in range(0, total_count, batch_size):
                temp = graph_client.graph_session.make_request(method='get',
                                    endpoint="/me/messages?$top={0}&$skip={1}"
                                    .format(batch_size, skip))
                
                content.append(temp[1]['value'])
        content = list(chain(*content))
        
        return content
        
        
        
            
            
            

        
        