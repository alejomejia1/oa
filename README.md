Libreria para conectarse a LENEL OpenAccess

Ejemplo de uso:


app.py 
```python
from OpenAccess import *
from python-dotenv import dotenv_values

oa = OpenAccess()
config = dotenv_values(.env)

# Sign-In
result = oa.sign_in(config["USERNAME"], config["PASSWORD"], config["DIRECTORY"])
print(result)
print("Session_Token:", oa.session_token)
input("Press Enter to continue...")

# GetPanels
print("Get Panels")
panels = oa.retrieve_panels()
print (panels)

input("Get Readers... Press Enter to continue...")
# GerReaders PanelID = 9
readers = oa.retrieve_readers(9)
print(readers)

input("Get Cardholder where SSNO = xxxxx ... Press Enter to continue...")
# GetCardHolder Where SSNO = "80109842"
cardholder = oa.request_cardholder(autoload_badge=1, has_badges=1, cardholder_filter='SSNO="80109842"')
print(cardholder)

input("Get Cardholder where BadgeID = xxxxx ... Press Enter to continue...")
# GetCardHolder Where BadgeId = "1944"
cardholder = oa.request_cardholder(autoload_badge=1, has_badges=1, badges_filter='ID="1944"')
print(cardholder)

```

.env
```
USERNAME=<username>
PASSWORD=<password>
DIRECTORY=<directory>
API_URL=http://localhost:8080
DEFAULT_PAGE_SIZE=10
SUCCESS=success
ERROR=error
API_VERSION=1.0
APPLICATION_ID=OpenAccess_app_id
```