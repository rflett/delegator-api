from sys import exit

import requests

r = requests.get("http://localhost:5000/health/")
exit() if r.status_code == 200 else exit(1)
