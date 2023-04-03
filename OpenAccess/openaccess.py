import requests
import json
from python-dotenv import load_dotenv, dotenv_values
import logging
from urllib.parse import urljoin

class OpenAccess:
    config = dotenv_values(".env")  # take environment variables from .env.
    # Constants and globals used throughout the class
    instance = None
    # Change 'localhost' to the fully qualified domain name where the OpenAccess service is hosted
    API_URL = config['API_URL']
    DEFAULT_PAGE_SIZE = config['DEFAULT_PAGE_SIZE']
    SUCCESS = config['SUCCESS']
    ERROR = config['ERROR']
    API_VERSION = config['API_VERSION']
    APPLICATION_ID = config['APPLICATION_ID']

    def __init__(self):
        # Set up the requests.Session to handle requests to the OpenAccess API
        self.base_url = self.API_URL
        self.client = requests.Session()
        self.client.headers.clear()
        self.client.headers.update({
            "Application-Id": self.APPLICATION_ID,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
        self.client.verify = False # Temporary solution for invalid security certificate causing an inability to access the api
        self.client.base_url = self.API_URL
        self.panels = []

        # You must initialize logging, otherwise you'll not see debug output.
        logging.basicConfig()
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True

    @staticmethod
    def instance():
        if not OpenAccess._instance:
            OpenAccess._instance = OpenAccess()
        return OpenAccess._instance
    

    def parse_response(self, response):
        return json.loads(response.content.decode('utf-8'))

    def build_uri_with_version(self, method_name, version):
        return "{}{}?version={}".format(self.base_url, method_name, version)

    def request_instances(self, type, page_num, panel_id=-1):
        request = self.build_uri_with_version("instances", "1.0") + f"&type_name={type}&page_number={page_num}&page_size={self.DEFAULT_PAGE_SIZE}&order_by=name"
        
        if panel_id != -1:
            request += f"&filter=panelid = {panel_id}"
    
        # OpenAccess "instances" request
        # GET /api/access/onguard/openaccess/instances
        # Retrieves instances of a particular type based on the client-supplied filter (above)
        response = self.client.get(request)
        
        return self.parse_response(response)

    def get_panels_from_result(self, result):
        panels = []
        for jo in result['item_list']:
            panels.append({
                'id': jo['property_value_map']['ID'],
                'name': jo['property_value_map']['Name'],
                'status': jo['property_value_map']['IsOnline'] == True,
                'type': jo['property_value_map']['PanelType']
            })
        return panels

    def get_readers_from_result(self, result):
        readers = []
        for jo in result['item_list']:
            readers.append({
                'panelId': jo['property_value_map']['PanelID'],
                'id': jo['property_value_map']['ReaderID'],
                'name': jo['property_value_map']['Name'],
                'type': jo['property_value_map']['ControlType'],
                'hostName': jo['property_value_map']['HostName']
            })
        return readers
    
    def request_cardholder(self, autoload_badge=False, has_badges=False, cardholder_filter=None,badges_filter=None ):
        # parameter = {
        #     "auto_load_badge":True
        # }

        request = self.build_uri_with_version("cardholders", "1.2")

        if autoload_badge:
            request += f"&auto_load_badge=true"
        

        if cardholder_filter is not None:
            request += f"&cardholder_filter={cardholder_filter}"
    
        if badges_filter is not None:
            request += f"&badges_filter={badges_filter}"

        # OpenAccess "cardholders" request
        # GET /api/access/onguard/openaccess/cardholders
        # Retrieves cardholders based on the client-supplied filter (above)
        response = self.client.get(request)
        
        return self.parse_response(response)
    
    def sign_in(self, username: str, password: str, directory_id: str) -> str:
        """
        OpenAccess "authentication" request

        POST /api/access/onguard/openaccess/authentication

        Logs a user into the OpenAccess service by validating their username and password, then
        returns a session token for further calls
        """

        # Create a User object to be serialized to JSON and sent as the payload in the POST request
        user = {"user_name": username, "password": password, "directory_id": directory_id}
        try:
            url = self.build_uri_with_version("authentication","1.0")
            print(url)
            response = requests.post(url, json=user, verify = False, headers = self.client.headers)
        except requests.exceptions.RequestException as e:
            return f"Connection was unexpectedly closed. Make sure you don't have anything other than OpenAccess running on port 8080. Message: {e}"

        # If a response is received, parse it into a dictionary so its properties can be retrieved easily
        if response.ok:
            result = self.parse_response(response)
            self.session_token = result["session_token"]
            self.client.headers.update({"Session-Token": self.session_token})
            return OpenAccess.SUCCESS

        # If an error occurred on the server side, return its information
        else:
            return f"A server error occurred during your request. If the status code is available, it is shown below\n{response.status_code}: {response.reason}"
        

    def get_directories(self):
        response = self.client.get(self.build_uri_with_version("directories","1.0"))

        # If a response is received, parse it into a dictionary so its properties can be retrieved easily
        if response.status_code == 200:
            directories = []
            result = json.loads(response.text)

            for directory in result['item_list']:
                directories.append({
                    'Id': directory['property_value_map']['ID'],
                    'Name': directory['property_value_map']['Name']
                })
            return directories
        # If an error occurred on the server side, return None
        else:
            return None
        
    def retrieve_panels(self):
        self.panels = []  # List to hold Panel objects to be displayed

        # Request the first page of panels
        result = self.request_instances("Lnl_Panel", 1)

        pageCount = result['total_pages']  # Number of pages to iterate over.

        # Convert the response to Panel objects and add them to the list
        self.panels.extend(self.get_panels_from_result(result))

        # Make a GET request for each page of panels we need
        for i in range(2, pageCount + 1):
            # Request the appropriate page of Panels
            result = self.request_instances("Lnl_Panel", i)

            # Convert the response to Panel objects and add them to the list
            self.panels.extend(self.get_panels_from_result(result))

        return self.panels

    def get_panels(self):
        return self.panels

    def retrieve_readers(self, panelId):
        readers = [] # List to hold Reader objects to be displayed

        # Request the first page of readers for the specified panel
        result = self.request_instances("Lnl_Reader", 1, panelId)

        if result["count"] == 0:
            return readers

        pageCount = result["total_pages"] # Number of pages to iterate over.

        # Convert the response to Reader objects and add them to the list
        readers.extend(self.get_readers_from_result(result))

        # Make a GET request for each page of readers we need
        for i in range(2, pageCount + 1):
            # Request the appropriate page of readers for the specified Panel
            result = self.request_instances("Lnl_Reader", i, panelId)

            # Convert the response to Reader objects and add them to the list
            readers.extend(self.get_readers_from_result(result))

        return readers
    
    def OpenDoor(self, reader):
        """
        OpenAccess "execute_method" request

        POST /api/access/onguard/openaccess/execute_method

        Executes a supported method against a specific instance of a particular type (OpenDoor() against a reader in this case)
        """
        # Dictionary of identifying attributes
        prop_value = {
            "PanelID": str(reader.panelId), 
            "ReaderID": str(reader.id)
        }

        # Dictionary of method parameters (none)
        parameter_value = {}

        # Data object to be serialized by PostAsJsonAsync
        em = {
            "method_name":"OpenDoor", 
            "type_name":"Lnl_Reader", 
            "property_value_map":prop_value, 
            "in_parameter_value_map":parameter_value
        }

        
        response = self.client.post_json(self.build_uri_with_version("execute_method"), em)

        # If a response is recieved, parse it into a dict so its properties can be retrieved easily
        if response.status_code == 200:
            return self.SUCCESS

        # If an error occurred on the server side, return its information
        else:
            return f"A server error occurred during your request. If the status code is available, it is shown below\n{response.status_code}: {response.text}"
