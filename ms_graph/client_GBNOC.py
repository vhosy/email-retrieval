import json
import time
import urllib
import random
import string
import pathlib

from typing import List
from typing import Dict

import msal
from ms_graph.session_GBNOC import GraphSession

from ms_graph.mail_GBNOC import Mail


class MicrosoftGraphClient:

    """
    ### Overview:
    ----
    Used as the main entry point for the Microsoft Graph
    API Service.
    """

    AUTHORITY_URL = "https://login.microsoftonline.com/"
    RESOURCE = "https://graph.microsoft.com/"
#     RESOURCE = "https://outlook.office.com/api/"
#     RESOURCE = "https://dev.outlook.com/"
    AUTH_ENDPOINT = "/oauth2/v2.0/authorize?"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scope: List[str],
#         account_type: str = "consumers",
#         account_type: str = "common",
        account_type: str = "{beb276ac-6e9f-498e-8e31-019ee666decd}", # add tenantID
        # office365: bool = False,
        credentials: str = None,
    ):
        """Initializes the Graph Client.

        ### Parameters
        ----
        client_id : str
            The application Client ID assigned when
            creating a new Microsoft App.

        client_secret : str
            The application Client Secret assigned when
            creating a new Microsoft App.

        redirect_uri : str
            The application Redirect URI assigned when
            creating a new Microsoft App.

        scope : List[str]
            The list of scopes you want the application
            to have access to.

        account_type : str, optional
            [description], by default "common"

        office365 : bool, optional
            [description], by default False
        """

        # printing lowercase
        letters = string.ascii_lowercase

        self.credentials = credentials
        self.token_dict = None

        self.client_id = client_id
        self.client_secret = client_secret
        self.api_version = "v1.0"
#         self.api_version = "v2.0"
        self.account_type = account_type
        self.redirect_uri = redirect_uri

        self.scope = scope
        self.state = "".join(random.choice(letters) for i in range(10))

        self.access_token = None
        self.refresh_token = None
        self.graph_session = None
        self.id_token = None

        # self.base_url = self.RESOURCE + self.api_version + "/"
        # self.office_url = self.OFFICE365_AUTHORITY_URL + self.OFFICE365_AUTH_ENDPOINT
        # self.graph_url = self.AUTHORITY_URL + self.account_type + self.AUTH_ENDPOINT
        # self.office365 = office365
        self._redirect_code = None

        # Initialize the Credential App.
        # print("------Initialize the Credential App------------")
        self.client_app = msal.ConfidentialClientApplication(
            client_id=self.client_id,
            authority=self.AUTHORITY_URL + self.account_type,
            client_credential=self.client_secret,
            # proxies={"http":"user:passwaord@proxy"}
        )
        # print("self.client_app",self.client_app.__dict__)
        # print("-----------Success-----------------------")

    

    

    def _token_validation(self, nseconds: int = 60):
        """Checks if a token is valid.

        Verify the current access token is valid for at least N seconds, and
        if not then attempt to refresh it. Can be used to assure a valid token
        before making a call to the TD Ameritrade API.

        Arguments:
        ----
        nseconds {int} -- The minimum number of seconds the token has to be
            valid for before attempting to get a refresh token. (default: {5})
        """

        if self._token_seconds(token_type="access_token") < nseconds:
            self.grab_refresh_token()

    

    

    

    def grab_access_token(self) -> Dict:
        """Exchanges a code for an Access Token.

        ### Returns:
        ----
        dict : A dictionary containing a new access token and refresh token.
        """

        # Parse the Code.
        query_dict = urllib.parse.parse_qs(self._redirect_code)

        # Grab the Code.
        code = query_dict[self.redirect_uri + "?code"]

#         Grab the Token.
#         TODO: Donot pass scope and see if can run
        token_dict = self.client_app.acquire_token_by_authorization_code(
            code=code, scopes=self.scope, redirect_uri=self.redirect_uri
        )
    
#         print("-----token_dict-----")
#         print(token_dict)

        # Save the token dict.
        self._state(action="save", token_dict=token_dict)

        return token_dict

    def authorization_url(self):
        """Builds the authorization URL used to get an Authorization Code.

        ### Returns:
        ----
        A string.
        """

        # Build the Auth URL.
        auth_url = self.client_app.get_authorization_request_url(
            scopes=self.scope, state=self.state, redirect_uri=self.redirect_uri
        )

        return auth_url

    def grab_refresh_token(self) -> Dict:
        """Grabs a new access token using a refresh token.

        ### Returns
        ----
        dict :
            A token dictionary with a new access token.
        """

        # Grab a new token using our refresh token.
        print("---Grab a new token using our refresh token.----")
#         print(self.refresh_token)
#         print(self.scope)
        token_dict = self.client_app.acquire_token_by_refresh_token(
            refresh_token=self.refresh_token, scopes=self.scope
        )

        if "error" in token_dict:
            print(token_dict)
            raise PermissionError(
                "Permissions not authorized, delete json file and run again. Refresh token has expired"
            )

        # Save the Token.
        self._state(action="save", token_dict=token_dict)

        return token_dict


    def _token_seconds(self, token_type: str = "access_token") -> int:
        """Determines time till expiration for a token.

        Return the number of seconds until the current access token or refresh token
        will expire. The default value is access token because this is the most commonly used
        token during requests.

        ### Arguments:
        ----
        token_type {str} --  The type of token you would like to determine lifespan for.
            Possible values are ["access_token", "refresh_token"] (default: {access_token})

        ### Returns:
        ----
        {int} -- The number of seconds till expiration.
        """

        # if needed check the access token.
        if token_type == "access_token":

            # if the time to expiration is less than or equal to 0, return 0.
            if not self.access_token or (
                time.time() + 60 >= self.token_dict["expires_in"]
            ):
                return 0

            # else return the number of seconds until expiration.
            token_exp = int(self.token_dict["expires_in"] - time.time() - 60)

        # if needed check the refresh token.
        elif token_type == "refresh_token":

            # if the time to expiration is less than or equal to 0, return 0.
            if not self.refresh_token or (
                time.time() + 60 >= self.token_dict["ext_expires_in"]
            ):
                return 0

            # else return the number of seconds until expiration.
            token_exp = int(self.token_dict["ext_expires_in"] - time.time() - 60)

        return token_exp


    def _silent_sso(self) -> bool:
        """Attempts a Silent Authentication using the Access Token and Refresh Token.

        Returns
        ----
        (bool)
            `True` if it was successful and `False` if it failed.
        """

        # if the current access token is not expired then we are still authenticated.
        if self._token_seconds(token_type="access_token") > 0:
            print("--if the current access token is not expired then we are still authenticated--")
            return True

        # if the current access token is expired then try and refresh access token.
        elif self.refresh_token and self.grab_refresh_token():
            print(" sucess: if the current access token is expired then try and refresh access token")
            return True

        # More than likely a first time login, so can"t do silent authenticaiton.
        print("----cannot do silent authenticaiton----")
        return False


    def _state(self, action: str, token_dict: dict = None) -> bool:
        """Sets the session state for the Client Library.

        ### Arguments
        ----
        action : str
            Defines what action to take when determining the state. Either
            `load` or `save`.

        token_dict : dict, optional
            If the state is defined as `save` then pass through the
            token dictionary you want to save, by default None.

        ### Returns
        ----
        bool:
            If the state action was successful, then returns `True`
            otherwise it returns `False`.
        """

        # Determine if the Credentials file exists.
        does_exists = pathlib.Path(self.credentials).exists()

        # If it exists and we are loading it then proceed.
        if does_exists and action == "load":
#             print("----inside credential path -----")

            # Load the file.
            with open(file=self.credentials, mode="r", encoding="utf-8") as state_file:
                credentials = json.load(fp=state_file)
                
#             print("----credentials------")
#             print(credentials)

            # Grab the Token if it exists.
            if "refresh_token" in credentials:
                print("----refresh token exist return True-----")

                self.refresh_token = credentials["refresh_token"]
                self.access_token = credentials["access_token"]
                self.id_token = credentials["id_token"]
                self.token_dict = credentials

                return True

            else:
                print("----refresh token doesnot exist return False-----")
                return False

        # If we are saving the state then open the file and dump the dictionary.
        elif action == "save":
            print("----save the refresh token-----")

            token_dict["expires_in"] = time.time() + int(token_dict["expires_in"])
            token_dict["ext_expires_in"] = time.time() + int(
                token_dict["ext_expires_in"]
            )

            self.refresh_token = token_dict["refresh_token"]
            self.access_token = token_dict["access_token"]
            self.id_token = token_dict["id_token"]
            self.token_dict = token_dict

            with open(file=self.credentials, mode="w+", encoding="utf-8") as state_file:
                json.dump(obj=token_dict, fp=state_file, indent=2)


    def login(self) -> None:
        """Logs the user into the session."""

        # Load the State.
        self._state(action="load")
        print("---state return succesfully----")

        # Try a Silent SSO First.
        if self._silent_sso():
            print("----inside _silent_sso------")

            # Set the Session.
            self.graph_session = GraphSession(client=self)

            return True

        else:
            print("----inside new authorization-----")

            # Build the URL.
            url = self.authorization_url()

            # aks the user to go to the URL provided, they will be prompted
            # to authenticate themsevles.
            print(f"Please go to URL provided authorize your account: {url}")

            # ask the user to take the final URL after authentication and
            # paste here so we can parse.
            my_response = input("Paste the full URL redirect here: ")

            # store the redirect URL
            self._redirect_code = my_response

            # this will complete the final part of the authentication process.
            self.grab_access_token()

            # Set the session.
            self.graph_session = GraphSession(client=self)

    

    def mail(self) -> Mail:
        """Used to access the Mail Services and metadata.

        ### Returns
        ---
        Mail:
            The `Mail` services Object.
        """

        # Grab the `Mail` Object for the session.
        mail_service: Mail = Mail(session=self.graph_session)

        return mail_service
    
    def list_of_sites(self) -> dict:
        content = self.graph_session.make_request(method="get", endpoint="/sites/root/lists")
        # content = json.dumps(content.json(), indent=4)
        return content