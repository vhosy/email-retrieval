Sometimes we just have too many emails in our inbox and folders, there's an email that we want to find but can only vaguely remember bits and pieces of its content.  Hence this code was created so that user can query in free form text on the email that they want and the function would return top N relevant emails.

Example:
find_email('which is the email from kohei where he approved uat for lan wan ip extension?')

Returns a pandas dataframe containing the email message, sent date, sender's name and email, receipients' names and emails.


