#!/usr/bin/env python2
import argparse
import os
import sys
from pprint import pprint

import shutil
from jinja2 import Environment, FileSystemLoader
import pydash

from scraper import *

from util import *


def update_java_data(data, config, update_all_versions=False):
    scraper = OracleJavaScraper(config)
    pydash.objects.merge(data, {'products': scraper.list_urls()}, {'last_updated': datetime_to_timestamp()})
    return data


def get_base_repository_info(config):
    base_repositories = config.get('base_repositories')
    base_repository_info_list = []
    for base_repository in base_repositories:
        image_name_components = parse_image_name(base_repository)
        full_repo = image_name_components.get('full_repo')
        registry = image_name_components.get('registry')
        repo = image_name_components.get('repo')
        tag = image_name_components.get('tag')

        pprint(image_name_components)

        i = repo.rfind('/')
        if i != -1:
            base_repository_name = repo[i + 1:]
        else:
            base_repository_name = repo

        registry_config = {}
        if registry is not None:
            registry_config_file = os.path.join(os.getcwd(), 'registries', registry + '.yml')
            if os.path.exists(registry_config_file):
                registry_config = load_yaml(registry_config_file)
                pprint(registry_config_file)
                pprint(registry_config)
            else:
                registry_config = pydash.get(config, ['base_repository_registries', registry], {})

        if tag is not None:
            tags = [tag]
        else:
            tags = list_repository_tags(repo,
                                        registry=registry,
                                        username=registry_config.get('username'),
                                        password=registry_config.get('password'),
                                        verify=registry_config.get('verify'))

        tags = [tag for tag in tags if tag != 'latest']
        tag_groups = group_tags(tags)

        base_repository_info = pydash.merge(image_name_components,
                                            {'name': base_repository_name,
                                             'tags': tags,
                                             'tag_groups': tag_groups})

        base_repository_info_list.append(base_repository_info)

    return base_repository_info_list


def render_java_dockerfiles(data, config, update_all_versions=False, force_update=False):
    env = Environment(loader=FileSystemLoader(os.path.abspath('templates')))
    repository_name = config['repository_name']
    base_repositories = config['base_repositories']
    template_files = config['templates']
    common_files = config['common_files']
    registries = config.get('registries')

    base_repository_info_list = get_base_repository_info(config)

    for product in ['jdk', 'jre', 'server-jre']:

        versions = data['products'][product].keys()

        if update_all_versions:
            versions_to_update = versions
        else:
            versions_to_update = filter_latest_versions(versions,
                                                        version_constraints=config.get('version_constraints'),
                                                        normalize_version=normalize_version_to_semver)

        for version in versions_to_update:
            version_files = data['products'][product][version]

            for base_repository_info in base_repository_info_list:
                base_repository_full_repo = base_repository_info['full_repo']
                base_repository_tag_groups = base_repository_info['tag_groups']
                base_repository_name = base_repository_info['name']

                for base_repository_tag_group in base_repository_tag_groups:
                    base_repository_main_tag = base_repository_tag_group[0]
                    base_image_name = base_repository_full_repo + ':' + base_repository_main_tag

                    dockerfile_context = os.path.join(os.getcwd(), product, version,
                                                      base_repository_name + base_repository_main_tag)

                    tags = [version]
                    for base_repository_tag in base_repository_tag_group:
                        tags.append(version + '-' + base_repository_name + base_repository_tag)

                    version_info = semver.parse_version_info(normalize_version_to_semver(version))

                    base_os = re.compile('centos|alpine|ubuntu|debian|fedora|rhel').search(
                        base_repository_name + base_repository_main_tag).group(0)

                    render_data = {
                        'base_image_name': base_image_name,
                        'base_os': base_os,
                        'base_repository_name': base_repository_name,
                        'config': config,
                        'files': version_files,
                        'jce': data['products']['jce'][str(version_info.major)],
                        'product': product,
                        'registries': registries,
                        'repository_name': repository_name + '-' + product,
                        'tags': tags,
                        'version': version,
                        'version_info': version_info,
                    }

                    pprint(render_data)

                    for template_file in template_files:
                        template_filenames = [
                            template_file + '.' + product + '.' + base_repository_name + base_repository_main_tag + '.j2',
                            template_file + '.' + product + '.' + base_repository_name + '.j2',
                            template_file + '.' + base_repository_name + '.j2',
                            template_file + '.j2'
                        ]

                        template = env.select_template(template_filenames)
                        template_render_path = os.path.join(dockerfile_context, template_file)
                        if not os.path.exists(template_render_path) or force_update:
                            write_file(template_render_path, template.render(render_data))
                            print 'Rendered template: ' + template_render_path

                    for common_file in common_files:
                        common_file_path = os.path.join(dockerfile_context, common_file)
                        if not os.path.exists(common_file_path) or force_update:
                            shutil.copy2(common_file, common_file_path)
                            print 'Copied file: ' + common_file_path


def main(argv):
    parser = argparse.ArgumentParser(description='Updates data file with urls and renders Dockerfiles.')
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

    saved_data = load_data_file(data_file)
    if saved_data is not None:
        data, _, update = saved_data
        perform_update = update or force_update
    else:
        data = {'products': {}}
        perform_update = True

    pprint(data)
    pprint(perform_update)

    if perform_update:
        data = update_java_data(data, config, update_all)
        write_yaml(data_file, data)
        print ('Updated data file: ' + data_file)

    render_java_dockerfiles(data, config, update_all, force_update)


if __name__ == '__main__':
    main(sys.argv)
