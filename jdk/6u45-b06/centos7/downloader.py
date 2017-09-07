#!/usr/bin/env python2
import argparse
import cookielib
import re
import urllib
import urllib2
import os
import sys

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
ORACLE_LOGIN_URL = "https://login.oracle.com/oam/server/sso/auth_cred_submit"


class Agent:
    def __init__(self, user_agent=None, debug=False):
        self.cookies = cookielib.LWPCookieJar()
        handlers = [
            urllib2.HTTPHandler(debuglevel=1 if debug else None),
            urllib2.HTTPSHandler(debuglevel=1 if debug else None),
            urllib2.HTTPCookieProcessor(self.cookies)
        ]
        self.opener = urllib2.build_opener(*handlers)

        self.opener.addheaders = [("Accept", "text/html"),
                                  ("User-Agent", user_agent if user_agent is not None else DEFAULT_USER_AGENT)]

        cookie = cookielib.Cookie(
            None,
            'oraclelicense',
            'accept-securebackup-cookie',
            None, False,
            '.oracle.com', True, True,
            '/', True,
            False,
            None,
            False,
            None,
            None,
            False
        )

        self.cookies.set_cookie(cookie)

    def get(self, url):
        request = urllib2.Request(url)
        response = self.opener.open(request)
        return response

    def post(self, url, data):
        if isinstance(data, dict):
            data = urllib.urlencode(data)

        request = urllib2.Request(url, data=data)
        request.get_method = lambda: 'POST'
        response = self.opener.open(request)

        return response


def download_oracle_java(url, filename, username, password, agent=None):
    if agent is None:
        agent = Agent()

    response = agent.get(url)
    if response.headers.get('Content-Type').startswith('text/html'):
        form = parse_login_form(html=response.read())
        form_data = {
            'v': 'v1.4',
            'OAM_REQ': form['OAM_REQ'],
            'site2pstoretoken': form['site2pstoretoken'],
            'locale': '',
            'ssousername': username,
            'password': password
        }

        response = agent.post(ORACLE_LOGIN_URL, data=form_data)

    with open(filename, mode='w') as file_handle:
        file_handle.write(response.read())


def parse_login_form(html):
    def parse_attributes(attributes_string):
        tag_attributes = {}
        attribute_pattern = re.compile('(\w+)="([^"]+)"')
        for attribute_pattern_match in attribute_pattern.finditer(attributes_string):
            tag_attributes[attribute_pattern_match.group(1)] = attribute_pattern_match.group(2)
        return tag_attributes

    form_tag_pattern = re.compile('<form([^>]+)>(.+)</form>')
    input_tag_pattern = re.compile('<input([^>]+)>')

    form_tag_pattern_match = form_tag_pattern.search(html)
    form_attributes_string = form_tag_pattern_match.group(1)
    form_contents = form_tag_pattern_match.group(2)

    form_tag_attributes = parse_attributes(form_attributes_string)

    form = {}

    for input_tag_pattern_match in input_tag_pattern.finditer(form_contents):
        input_attributes_string = input_tag_pattern_match.group(1)
        input_tag_attributes = parse_attributes(input_attributes_string)

        name = input_tag_attributes.get('name')
        value = input_tag_attributes.get('value')
        if name:
            form[name] = value

    return form


def main(argv):
    parser = argparse.ArgumentParser(description='Downloads Oracle Java.')
    parser.add_argument('--user-agent', nargs='?', dest='user_agent', default=DEFAULT_USER_AGENT)
    parser.add_argument('--username', nargs='?', dest='username')
    parser.add_argument('--password', nargs='?', dest='password')
    parser.add_argument('--url', nargs='?', dest='url')
    parser.add_argument('--filename', nargs='?', dest='filename')
    parser.add_argument('--debug', dest='debug', action='store_true')

    parsed_args = vars(parser.parse_args())

    user_agent = parsed_args.get('user_agent') or DEFAULT_USER_AGENT
    username = parsed_args.get('username')
    password = parsed_args.get('password')
    url = parsed_args.get('url')
    filename = parsed_args.get('filename') or url[url.rfind('/') + 1:]
    debug = parsed_args.get('debug')

    missing_parameter = False
    if url is None:
        print ('Missing parameter: url')
        missing_parameter = True
    if filename is None:
        print ('Missing parameter: filename')
        missing_parameter = True
    if username is None:
        print ('Missing parameter: username')
        missing_parameter = True
    if password is None:
        print ('Missing parameter: password')
        missing_parameter = True
    if missing_parameter:
        parser.print_help()
        exit(1)

    agent = Agent(user_agent=user_agent, debug=debug)
    download_oracle_java(url=url, filename=filename, username=username, password=password, agent=agent)


if __name__ == '__main__':
    main(sys.argv)
