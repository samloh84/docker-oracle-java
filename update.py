#!/usr/bin/env python2

import os, sys, json, re, urlparse, errno, time, argparse
from datetime import datetime, timedelta

import shutil
import yaml, semver, requests, grequests, jinja2
from bs4 import BeautifulSoup

ORACLE_JAVA_DOWNLOADS_URL = "http://www.oracle.com/technetwork/java/javase/downloads/index.html"
ORACLE_JAVA_ARCHIVED_DOWNLOADS_URL = "http://www.oracle.com/technetwork/java/javase/archive-139210.html"
ORACLE_JCE7_DOWNLOADS_URL = "http://www.oracle.com/technetwork/es/java/javase/downloads/jce-7-download-432124.html"


def http_get(url, headers=None):
    return requests.get(url, headers=headers)


def http_multiget(urls, headers=None):
    return zip(urls, grequests.map([grequests.get(url, headers=headers) for url in urls]))


def _get(obj, path):
    curr_obj = obj
    if not isinstance(path, list):
        path = [path]

    for path_segment in path:
        curr_obj = curr_obj.get(path_segment)
        if curr_obj is None:
            break
    return curr_obj


def _set(obj, path, value):
    curr_obj = obj
    if not isinstance(path, list):
        path = [path]
    for path_segment in path[:-1]:
        if curr_obj.get(path_segment) is None:
            curr_obj[path_segment] = {}
        curr_obj = curr_obj.get(path_segment)
    curr_obj[path[-1]] = value


def list_docker_hub_image_tags(repository):
    url = "https://hub.docker.com/v2/repositories/" + repository + "/tags"
    request_headers = {'Accept': 'application/json'}

    tags = []

    while url is not None:
        response_data = http_get(url, headers=request_headers).json()
        tags += response_data["results"]
        url = response_data["next"]

    return tags


def list_oracle_java_downloads():
    java_se_download_urls = []

    java_downloads_response = http_get(ORACLE_JAVA_DOWNLOADS_URL)
    java_downloads_soup = BeautifulSoup(java_downloads_response.text, 'html.parser')

    java_downloads_url_pattern = re.compile('/technetwork/java/javase/downloads/(jdk|server-jre|jre|jce)')
    java_downloads_links = java_downloads_soup.find_all('a', href=java_downloads_url_pattern)

    java_downloads_urls = map(lambda link: urlparse.urljoin(ORACLE_JAVA_DOWNLOADS_URL, link['href']),
                              java_downloads_links)

    java_archived_downloads_url_pattern = re.compile('/technetwork/java/(javase|javasebusiness)/downloads/'
                                                     + 'java-archive(-downloads)?-(javase|java-client|java-plat)')

    java_archived_downloads_response = http_get(ORACLE_JAVA_ARCHIVED_DOWNLOADS_URL)
    java_archived_downloads_soup = BeautifulSoup(java_archived_downloads_response.text, 'html.parser')

    java_archived_downloads_links = java_archived_downloads_soup.find_all('a', href=java_archived_downloads_url_pattern)

    java_downloads_urls += map(lambda link: urlparse.urljoin(ORACLE_JAVA_ARCHIVED_DOWNLOADS_URL, link['href']),
                               java_archived_downloads_links)

    java_downloads_urls += [ORACLE_JCE7_DOWNLOADS_URL]

    downloads = {}
    responses = http_multiget(java_downloads_urls)

    download_url_pattern = re.compile('downloads(?:\[\'.+\'\])+\s*=\s*{.*"filepath":"(.+?)".*};', flags=re.MULTILINE)

    version_pattern = re.compile('(\d+|\d+u\d+|\d+_\d+_\d+_\d+)-')
    system_pattern = re.compile('(linux-(?:x64|i386|i586|amd64))')
    extension_pattern = re.compile('((?:-rpm)?\.(?:tar\.gz|rpm|bin))')

    patterns = {
        'jdk': re.compile('j(?:2s)?dk-'
                          + version_pattern.pattern
                          + system_pattern.pattern
                          + extension_pattern.pattern),

        'jre': re.compile('j(?:2)?re-'
                          + version_pattern.pattern
                          + system_pattern.pattern
                          + extension_pattern.pattern),
        'server-jre': re.compile('server-jre-'
                                 + version_pattern.pattern
                                 + system_pattern.pattern
                                 + extension_pattern.pattern),
        'jce': re.compile('(?:jce(?:_policy)?-|UnlimitedJCEPolicyJDK)(\d+|\d+_\d+_\d+)(\.zip)')
    }

    for _, response in responses:
        response_soup = BeautifulSoup(response.text, 'html.parser')
        license_scripts = response_soup.find_all('script', text=re.compile('var downloads = new Array\(\);'))

        for script in license_scripts:
            for download_url_pattern_match in download_url_pattern.finditer(script.text):
                download_url = download_url_pattern_match.group(1)

                match = None
                for key, pattern in patterns.iteritems():
                    match = pattern.search(download_url)
                    if match:
                        if key == 'jce':
                            filename = match.group(0)
                            version = match.group(1)
                            extension = match.group(2)
                            major_version = parse_version(version)['major']

                            _set(downloads, [key, major_version, extension, 'filename'], filename)
                            _set(downloads, [key, major_version, extension, 'url'], download_url)
                        else:
                            filename = match.group(0)
                            version = match.group(1)
                            system = match.group(2)
                            extension = match.group(3)

                            _set(downloads, [key, version, system, extension, 'filename'], filename)
                            _set(downloads, [key, version, system, extension, 'url'], download_url)
                        break
    return downloads


def parse_version(version):
    version_patterns = [re.compile('1_(?P<major>\d+)_(?P<minor>\d+)(?:_(?P<patch>\d+))?'),
                        re.compile('(?P<major>\d+)u(?P<minor>\d+)'),
                        re.compile('(?P<major>\d+)')]

    for version_pattern in version_patterns:
        version_pattern_match = version_pattern.match(version)
        if version_pattern_match:
            return version_pattern_match.groupdict()
    return None


def compare_versions(version_a, version_b):
    version_a_info = parse_version(version_a)
    version_b_info = parse_version(version_b)

    if version_a_info is None and version_b_info is None:
        return 0
    elif version_a_info is not None and version_b_info is None:
        return -1
    elif version_a_info is None and version_b_info is not None:
        return 1

    for key in ['major', 'minor', 'patch']:
        if version_a_info.get(key) is None and version_b_info.get(key) is None:
            return 0
        elif version_a_info.get(key) is not None and version_b_info.get(key) is None:
            return -1
        elif version_a_info.get(key) is None and version_b_info.get(key) is not None:
            return 1
        elif int(version_a_info.get(key)) > int(version_b_info.get(key)):
            return -1
        elif int(version_a_info.get(key)) < int(version_b_info.get(key)):
            return 1

    return 0


def match_version(version, version_to_match):
    operator_pattern = re.compile('^(>=?|<=?|=)(.+)$')
    match = operator_pattern.match(version_to_match)
    if match:
        operator = match.group(1)
        _version_to_match = match.group(2)
    else:
        operator = '='
        _version_to_match = version_to_match
    comparison = compare_versions(version, _version_to_match)
    if (operator == '=' or operator == '>=' or operator == '<=') and comparison == 0:
        return True
    elif (operator == '>' or operator == '>=') and comparison < 0:
        return True
    elif (operator == '<' or operator == '<=') and comparison > 0:
        return True
    else:
        return False


def filter_latest_major_versions(versions, min_ver=None, max_ver=None):
    major_versions = {}

    for version in versions:
        if min_ver is not None:
            if not match_version(version, min_ver):
                continue

        if max_ver is not None:
            if not match_version(version, max_ver):
                continue

        major_version = parse_version(version)['major']
        current_major_version = major_versions.get(major_version)
        if current_major_version is None or compare_versions(version, current_major_version) < 0:
            major_versions[major_version] = version

    return major_versions.values()


def load_file(filename):
    filename = os.path.abspath(filename)
    with open(filename, 'r') as f:
        return f.read()


def load_yaml(filename):
    return yaml.safe_load(load_file(filename))


def write_file(filename, data):
    filename = os.path.abspath(filename)
    file_dir = os.path.dirname(filename)
    mkdirp(file_dir)
    with open(filename, 'w') as f:
        f.write(data)


def write_yaml(filename, data):
    write_file(filename, yaml.safe_dump(data, default_flow_style=False))


def datetime_to_timestamp(date=None):
    if date is None:
        date = datetime.now()
    return int(time.mktime(date.timetuple()))


def timestamp_to_datetime(timestamp):
    if timestamp is None or timestamp == "":
        return None
    return datetime.fromtimestamp(int(timestamp))


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass


def load_oracle_java_data(config, data_file, force_update=False, update_all_versions=False):
    current_datetime = datetime.now()
    current_timestamp = datetime_to_timestamp(current_datetime)

    oracle_java_data = {'jdk': {'versions': {}},
                        'jre': {'versions': {}},
                        'jce': {'versions': {}},
                        'server-jre': {'versions': {}}
                        }
    last_updated = None
    oracle_java_data_updated = False

    try:
        if os.path.isfile(data_file):
            oracle_java_data = load_yaml(data_file)
            last_updated = timestamp_to_datetime(oracle_java_data['last_updated'])
    except:
        pass

    update = force_update or last_updated is None or last_updated + timedelta(days=1) <= current_datetime

    products = ['jdk', 'jre', 'server-jre', 'jce']
    for key in products:
        if update:
            updated_oracle_java_data = list_oracle_java_downloads()
            versions = updated_oracle_java_data[key].keys()
            for version in versions:
                if _get(oracle_java_data, [key, 'versions', version, 'files']) is None:
                    _set(oracle_java_data, [key, 'versions', version, 'files'], updated_oracle_java_data[key][version])
            oracle_java_data_updated = True
        else:
            versions = oracle_java_data[key]['versions'].keys()

    if oracle_java_data_updated:
        oracle_java_data['last_updated'] = datetime_to_timestamp()
        write_yaml(data_file, oracle_java_data)
        print 'Updated ' + data_file

    return oracle_java_data


def render_dockerfiles(config, oracle_java_data, force_update=False):
    jinja2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.abspath('templates')))

    for product in ['jdk', 'jre', 'server-jre']:
        for base_repository in config['base_repositories']:
            base_repository_tags = [base_repository_tag['name'] for base_repository_tag in
                                    list_docker_hub_image_tags(base_repository) if
                                    base_repository_tag['name'] != 'latest']

            base_os = base_repository[base_repository.rfind('/') + 1:]

            dockerfile_template = jinja2_env.select_template(['Dockerfile.' + product + '.' + base_os + '.j2',
                                                              'Dockerfile.' + base_os + '.j2',
                                                              'Dockerfile.j2'])
            makefile_template = jinja2_env.select_template(['Makefile.' + product + '.' + base_os + '.j2',
                                                            'Makefile.' + base_os + '.j2',
                                                            'Makefile.j2'])

            latest_major_versions = filter_latest_major_versions(oracle_java_data[product]['versions'].keys(),
                                                                 min_ver=config.get('min_version'),
                                                                 max_ver=config.get('max_version'))

            for base_repository_tag in base_repository_tags:
                base_image_name = base_repository + ':' + base_repository_tag
                tag_suffix = base_os + base_repository_tag

                for version in latest_major_versions:
                    image_tags = [version, version + '-' + tag_suffix]
                    dockerfile_context = os.path.join(os.getcwd(), product, version, tag_suffix)

                    dockerfile_path = os.path.join(dockerfile_context, 'Dockerfile')
                    makefile_path = os.path.join(dockerfile_context, 'Makefile')

                    dockerfile_exists = os.path.exists(dockerfile_path)
                    makefile_exists = os.path.exists(makefile_path)

                    version_info = parse_version(version)

                    if force_update or not dockerfile_exists or not makefile_exists:
                        render_data = {
                            'product': 'oracle-java-' + product,
                            'version': version,
                            'version_info': version_info,
                            'repository_name': config['repository_name'] + '-' + product,
                            'base_os': base_os,
                            'base_image_name': base_image_name,
                            'tag_suffix': tag_suffix,
                            'dockerfile_context': dockerfile_context,
                            'image_tags': image_tags,
                            'files': oracle_java_data[product]['versions'][version]['files'],
                            'jce_files': oracle_java_data['jce']['versions'][version_info['major']]['files']
                        }

                        if force_update or not dockerfile_exists:
                            write_file(dockerfile_path, dockerfile_template.render(render_data))
                            print 'Generated ' + dockerfile_path
                        if force_update or not makefile_exists:
                            write_file(makefile_path, makefile_template.render(render_data))
                            print 'Generated ' + makefile_path

                    downloader_path = os.path.join(dockerfile_context, 'downloader.py')
                    downloader_exists = os.path.exists(downloader_path)
                    if force_update or not downloader_exists:
                        shutil.copyfile('downloader.py', downloader_path)
                        print 'Copied ' + downloader_path



def main(argv):
    parser = argparse.ArgumentParser(description='Updates Oracle Java data file with version URLs and Dockerfiles.')
    parser.add_argument('--data-file', nargs='?', dest='data_file', default=os.path.abspath('oracle_java.yml'))
    parser.add_argument('--config-file', nargs='?', dest='config_file', default=os.path.abspath('config.yml'))
    parser.add_argument('-f', '--force-update', dest='force_update', action='store_true')
    parser.add_argument('-a', '--update-all', dest='update_all', action='store_true')

    parsed_args = vars(parser.parse_args())

    config_file = parsed_args.get('config_file')
    data_file = parsed_args.get('data_file')
    force_update = parsed_args.get('force_update')
    update_all = parsed_args.get('update_all')

    config = load_yaml(config_file)

    oracle_java_data = load_oracle_java_data(config, data_file, force_update, update_all)
    render_dockerfiles(config, oracle_java_data, force_update)


if __name__ == '__main__':
    main(sys.argv)
