import getpass
import json
from restkit import Resource, BasicAuth, Connection, request
from socketpool import ConnectionPool

DEFAULT_HEADERS = {'Content-Type': 'application/json'}

# Color sequence from ColorBrewer http://colorbrewer2.org/
# Diverging 6 color BrBG scheme

DEFAULT_LABELS = (('0 - Backlog', '8C510A'),
                  ('1 - On Deck', 'D8B365'),
                  ('2 - Analysis', 'F6E8C3'),
                  ('3 - Developing', 'C7EAE5'),
                  ('4 - Acceptance', '5AB4AC'),
                  ('5 - Production Close', '01665E'),)

SERVER_URL = "https://api.github.com"

def post_api_payload(url, pool=None, filters=None, headers=DEFAULT_HEADERS, payload=None):
    res = Resource(url, pool=pool, filters=filters)
    return json.loads(res.post(headers=headers, payload=payload).body_string())

def get_api_payload(url, pool=None, filters=None, headers=DEFAULT_HEADERS):
    res = Resource(url, pool=pool, filters=filters)
    return json.loads(res.get(headers=headers).body_string())

def request_api_payload(url, action, payload=None, pool=None, headers=DEFAULT_HEADERS):
    res = Resource(url, pool=pool)
    return json.loads(res.request(action, payload=payload, headers=headers))

def get_all_repos(username, pool, headers):
    repos = {username: get_api_payload('{0}/user/repos'.format(SERVER_URL), pool=pool, headers=headers)}
    for org in get_api_payload('{0}/user/orgs'.format(SERVER_URL), pool=pool, headers=headers):
        repos[org['login']] = get_api_payload('{0}/orgs/{1}/repos'.format(SERVER_URL, org['login']), pool=pool, headers=headers)
    return repos

def main():
    pool = ConnectionPool(factory=Connection)

    print "This script will create the following default labels in your specified " \
        "repository if they do not yet exist: \n%s" % (',\n'.join(lab[0] for lab in DEFAULT_LABELS))

    repo = raw_input("Repository name: ")
    username = raw_input("Username: ")
    pwd = getpass.getpass("Password: ")
    auth=BasicAuth(username, pwd)

    # Use your basic auth to request a token
    # This is just an example from http://developer.github.com/v3/
    authreqdata = { "scopes": [ "repo" ], "note": "admin script" }
    token = post_api_payload('{0}/authorizations'.format(SERVER_URL), pool=pool, filters=[auth], payload=json.dumps(authreqdata))['token']

    #Once you have a token, you can pass that in the Authorization header
    #You can store this in a cache and throw away the user/password
    #This is just an example query.  See http://developer.github.com/v3/
    #for more about the url structure
    headers = {'Authorization': 'token {0}'.format(token)}
    headers.update(DEFAULT_HEADERS)
    repos = get_all_repos(username, pool, headers)
    for account in repos:
        for account_repo in repos[account]:
            if account_repo['has_issues'] and repo == account_repo['name']:
                labels = get_api_payload('{0}/repos/{1}/{2}/labels'.format(SERVER_URL, account, repo), pool=pool, headers=headers)
                label_names = [n['name'] for n in labels]

                for dl, color in DEFAULT_LABELS:
                    payload = {"name": dl, "color": color}
                    headers = {'Content-Type' : 'application/json' }
                    headers['Authorization'] = 'token %s' % token

                    if dl not in label_names:
                        print "Adding {0} to {1}/{2}".format(dl, account, repo)
                        post_api_payload('{0}/repos/{1}/{2}/labels'.format(SERVER_URL, account, repo), pool=pool, headers=headers, payload=json.dumps(payload))
                    else:
                        print "Updating colors for {0} in {1}/{2}".format(dl, account, repo)
                        request_api_payload('{0}/repos/{1}/{2}/labels{3}'.format(SERVER_URL, account, repo, dl), 'PATCH', payload=json.dumps(payload), headers=headers)


if __name__ == '__main__':
    main()
