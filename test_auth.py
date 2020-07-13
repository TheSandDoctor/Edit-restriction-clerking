import requests, userpassbot

S = requests.Session()
# Retrieve login token first
PARAMS_0 = {
    'action':"query",
    'meta':"tokens",
    'type':"login",
    'format':"json"
}

R = S.get(url="https://en.wikipedia.org/w/api.php", params=PARAMS_0)
DATA = R.json()
LOGIN_TOKEN = DATA['query']['tokens']['logintoken']

#print(LOGIN_TOKEN)

# Send a post request to login. Using the main account for login is not
# supported. Obtain credentials via Special:BotPasswords
# (https://www.mediawiki.org/wiki/Special:BotPasswords) for lgname & lgpassword

PARAMS_1 = {
    'action':"login",
    'lgname':userpassbot.username,
    'lgpassword':userpassbot.password,
    'lgtoken':LOGIN_TOKEN,
    'format':"json"
}

R = S.post("https://en.wikipedia.org/w/api.php", data=PARAMS_1)
DATA = R.json()

print(DATA)

# Step 3: When logged in, retrieve a CSRF token
PARAMS_2 = {
    'action':"query",
    'meta':"tokens",
    'format':"json"
}

R = S.get(url="https://en.wikipedia.org/w/api.php", params=PARAMS_2)
DATA = R.json()

CSRF_TOKEN = DATA['query']['tokens']['csrftoken']
print(CSRF_TOKEN)
params = {'action': 'query',
              'list': 'alldeletedrevisions',
              'adrprop': 'timestamp',
              'adrlimit': 1,
              'adruser': "TheSandDoctor",
              'adrdir': "older",
            'format': 'json',
              'token':CSRF_TOKEN,
              }
R = S.get("https://en.wikipedia.org/w/api.php", params=params)
result = R.json()
if len(result) > 2:
    founddate = result['query']['alldeletedrevisions'][0]['revisions'][0]['timestamp']
    print(founddate)