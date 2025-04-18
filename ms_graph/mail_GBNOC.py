from ms_graph.session_GBNOC import GraphSession
import json
import os
import base64


class Mail:

    """
    ## Overview:
    ----
    Microsoft Graph lets your app get authorized access to a user"s
    Outlook mail data in a personal or organization account. With the
    appropriate delegated or application mail permissions, your app can
    access the mail data of the signed-in user or any user in a tenant.
    """

    def __init__(self, session: object) -> None:
        """Initializes the `Mail` service.

        ### Parameters
        ----
        session : object
            An authenticated session for our Microsoft Graph Client.
        """

        # Set the session.
        self.graph_session: GraphSession = session

        # Set the endpoint.
        self.endpoint = "mail"

    def list_my_messages(self) -> dict:
        """Get the messages in the signed-in user"s mailbox
        (including the Deleted Items and Clutter folders).

        ### Returns
        ----
        dict
            If successful, this method returns a 200 OK response
            code and collection of `Message` objects in the response
            body.
        """

        # content = self.graph_session.make_request(method="get", endpoint="/me/messages")
        content = self.graph_session.make_request(method="get", endpoint="/me/mailFolders/inbox/messages/?top=10")
        # content = self.graph_session.make_request(method="get", endpoint="/me/mailFolders/inbox/messages/?$select=receivedDateTime,subject,sender,from,toRecipients,ccRecipients,bccRecipients,replyTo")
        
        # content = json.dumps(content.json(), indent=4)

        return content