#!/usr/bin/env python2
from pprint import pprint

import sys

from util import *
from pydash import set_ as _set, flatten as _flatten
from pydash.arrays import uniq as _uniq

ORACLE_JAVA_DOWNLOADS_URL = "http://www.oracle.com/technetwork/java/javase/downloads/index.html"
ORACLE_JAVA_ARCHIVED_DOWNLOADS_URL = "http://www.oracle.com/technetwork/java/javase/archive-139210.html"
ORACLE_JCE7_DOWNLOADS_URL = "http://www.oracle.com/technetwork/es/java/javase/downloads/jce-7-download-432124.html"


def parse_html_for_oracle_download_paths_scripts(html):
    bs = BeautifulSoup(html, 'html.parser')
    download_url_pattern = re.compile('downloads(?:\[\'.+\'\])+\s*=\s*{.*"filepath":"(.+?)".*};', flags=re.MULTILINE)
    scripts = bs.find_all('script', text=re.compile('var downloads = new Array\(\);'))
    download_urls = []
    for script in scripts:
        for download_url_pattern_match in download_url_pattern.finditer(script.text):
            download_url = download_url_pattern_match.group(1)
            download_urls.append(download_url)
    return download_urls


class OracleJavaScraper:
    def __init__(self, config):
        self.starting_urls = config['starting_urls']
        self.url_pattern = re.compile(config['url_pattern'])
        self.pattern_tree = PatternTree(config['file_patterns'])
        pass

    def list_urls(self, return_unmatched_urls=False):

        responses = []

        urls_to_parse = self.starting_urls
        url_pattern = self.url_pattern

        while len(urls_to_parse) > 0:
            curr_responses = http_multiget(urls_to_parse)
            responses += curr_responses
            parsed_urls = [url for (url, _) in responses]
            urls_to_parse = map(lambda (url, response): parse_html_for_urls(response.text, url, regex_filters=url_pattern),
                                curr_responses)
            urls_to_parse = _flatten(urls_to_parse)
            urls_to_parse = [url for url in urls_to_parse if url not in parsed_urls]

        download_urls = map(lambda (url, response): parse_html_for_oracle_download_paths_scripts(response.text),
                            responses)
        download_urls = _flatten(download_urls)

        version_files = {}
        unmatched_urls = []

        for parsed_url in download_urls:

            pattern_match = self.pattern_tree.search(parsed_url)

            if pattern_match is not None:
                match, pattern_match_path = pattern_match
                product = pattern_match_path[0]
                extension = pattern_match_path[1]

                if product == 'jce':
                    url_version = match.group(1)
                    filename = match.group(2)
                    path = [product, url_version, extension]
                else:
                    url_version = match.group(1)
                    filename = match.group(2)
                    distribution_os = match.group(3)
                    path = [product, url_version, distribution_os, extension]

                _set(version_files, path, {
                    'filename': filename,
                    'url': parsed_url
                })
            else:
                unmatched_urls.append(parsed_url)
        if return_unmatched_urls:
            version_files['unmatched_urls'] = unmatched_urls
        return version_files


def list_docker_hub_image_tags(repository):
    url = "https://hub.docker.com/v2/repositories/" + repository + "/tags"
    request_headers = {'Accept': 'application/json'}

    tags = []

    while url is not None:
        response_data = http_get(url, headers=request_headers).json()
        tags += response_data["results"]
        url = response_data["next"]

    return tags


def main(argv):
    config = load_yaml('config.yml')
    scraper = OracleJavaScraper(config)
    files = scraper.list_urls()
    print_yaml(files)


if __name__ == '__main__':
    main(sys.argv)
