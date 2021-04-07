import os

sysvar = os.environ

try:
    user = sysvar["fnetUSER"]
    passwd = sysvar["fnetPWD"]
except:
    user="utpal"
    passwd="9934036404"
