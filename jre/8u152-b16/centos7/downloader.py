#!/usr/bin/env python2
from HTMLParser import HTMLParser
import argparse
import cookielib
import re
import requests
import os
import sys
import urlparse

DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
ORACLE_LOGIN_URL = "https://login.oracle.com/oam/server/sso/auth_cred_submit"


class Agent:
    def __init__(self, user_agent=None, debug=False):
        self.session = requests.Session()
        self.session.cookies.set('oraclelicense', 'accept-securebackup-cookie', domain='.oracle.com', path='/')
        self.addheaders = {"Accept": "text/html",
                           "User-Agent": user_agent if user_agent is not None else DEFAULT_USER_AGENT}

    def get(self, url):
        return self.session.get(url, headers=self.addheaders)

    def post(self, url, data):
        return self.session.post(url, data)


def download_oracle_java(url, filename, username, password, agent=None):
    if agent is None:
        agent = Agent()
    oam_redirect_pattern = re.compile('JavaScript is required. Enable JavaScript to use OAM Server.')
    jump_page_pattern = re.compile('Logging in. Please wait...')
    jump_page2_pattern = re.compile('If you are not automatically transferred to the target, click here.')

    response = agent.get(url)

    if response.headers.get('Content-Type').startswith('text/html'):

        if oam_redirect_pattern.search(response.text) is not None:
            oam_form = parse_form(response.text)
            oam_redirect_url = urlparse.urljoin(response.url, oam_form['attributes']['action'])
            response = agent.post(oam_redirect_url,
                                  data=oam_form['fields'])

        login_form = parse_form(html=response.text)
        login_form_data = {}
        login_form_data.update(login_form['fields'])
        login_form_data.update({
            'userid': username,
            'pass': password
        })

        login_form_url = urlparse.urljoin(response.url, login_form['attributes']['action'])
        response = agent.post(login_form_url, data=login_form_data)

        if response.headers.get('Content-Type').startswith('text/html') \
                and jump_page_pattern.search(response.text) is not None:
            jump_page_meta = parse_meta(response.text)
            refresh_meta_pattern = re.compile('URL=(.*)')
            jump_page_url = refresh_meta_pattern.search(jump_page_meta['refresh']).group(1)
            jump_page_url = urlparse.urljoin(response.url, jump_page_url)
            response = agent.get(jump_page_url)

        if jump_page2_pattern.search(response.text) is not None:
            jump_page2_form = parse_form(response.text)
            jump_page2_redirect_url = urlparse.urljoin(response.url, jump_page2_form['attributes']['action'])
            response = agent.post(jump_page2_redirect_url,
                                  data=jump_page2_form['fields'])

    if response.headers.get('Content-Type').startswith('text/html'):
        raise RuntimeError('Invalid content type')

    with open(filename, mode='w') as file_handle:
        file_handle.write(response.content)


def parse_meta(html):
    class MetaParser(HTMLParser):
        def __init__(self):
            HTMLParser.__init__(self)
            self.meta = {}

        def handle_starttag(self, tag, attrs):
            if tag == 'meta':
                attributes = dict((key, value) for key, value in attrs)

                if attributes.get('http-equiv') is not None:
                    self.meta[attributes.get('http-equiv')] = attributes.get('content')

                return self.meta

    parser = MetaParser()

    parser.feed(html)
    parser.close()

    return parser.meta


def parse_form(html):
    class FormParser(HTMLParser):

        def __init__(self):
            HTMLParser.__init__(self)
            self.in_form = False
            self.form = {'attributes': {}, 'fields': {}}

        def handle_starttag(self, tag, attrs):

            if tag == 'form':
                self.in_form = True
                self.form['attributes'] = dict((key, value) for key, value in attrs)
            if self.in_form and tag == 'input':
                attributes = dict((key, value) for key, value in attrs)
                if attributes.get('name') is not None:
                    self.form['fields'][attributes['name']] = attributes.get('value')

        def handle_endtag(self, tag):
            if tag == 'form':
                self.in_form = False

    parser = FormParser()

    parser.feed(html)
    parser.close()

    return parser.form


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
