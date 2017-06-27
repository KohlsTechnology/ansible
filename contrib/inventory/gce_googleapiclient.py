#!/usr/bin/env python
"""Usage provided by docoptcfg using the global DOCOPT_USAGE constant"""

from __future__ import print_function

from os.path import basename
from sys import argv,exit

import collections
import logging as log
import json

from docoptcfg import docoptcfg
from docoptcfg import DocoptcfgFileError

from googleapiclient import discovery
from oauth2client.client import GoogleCredentials
from googleapiclient.errors import HttpError

ENV_PREFIX = 'GCE_'

DOCOPT_USAGE = """
Google Cloud Engine Dynamic Inventory
=====================================

Before using:

- Authentication: this script uses the same authentication as gcloud command line. So, set it up before.
- Dependencies: it depends mainly on google-api-python-client and docoptcfg. So:

$ pip install google-api-python-client docoptcfg

Usage:
    {script_name} [options]

Options:
    --account ACCOUNT_NAME --account=ACCOUNT_NAME  Billing account name
    -a API_VERSION --api-version=API_VERSION       The API version used to connect to GCE [default: v1]
    -c CONFIG_FILE --config=CONFIG_FILE            Path to the config file (see docoptcfg docs) [default: ./gce_googleapiclient.ini]
    -l --list                                      List all hosts (needed by Ansible, but actually doesn't do anything)
    -p PROJECT --project=PROJECT                   The GCE project where you want to get the inventory
    -z ZONE --zone=ZONE                            The GCE zone where you ant to get the inventory

All the parameters can also be set as environment variables using the 'GCE_' prefix (i.e. {envvar_prefix}API_VERSION=beta).
""".format(script_name=basename(argv[0]), envvar_prefix=ENV_PREFIX)



def get_all_billing_projects(billing_account_name, api_version='v1'):
    project_ids = []

    credentials = GoogleCredentials.get_application_default()

    service = discovery.build('cloudbilling', 
                              version=api_version,
                              credentials=credentials)
    # pylint: disable=no-member
    request = service.billingAccounts().projects().list(name=billing_account_name)

    while request is not None:
        response = request.execute()

        # pylint: disable=no-member
        request = service.billingAccounts().projects().list_next(previous_request=request,
                                                                 previous_response=response)

        for projectbillinginfo in response['projectBillingInfo']:
            if projectbillinginfo['billingEnabled']:
                project_ids.append(projectbillinginfo['projectId'])

    return project_ids

def get_all_zones_in_project(project, api_version='v1'):
    zones = []

    credentials = GoogleCredentials.get_application_default()
    service = discovery.build('compute', api_version, credentials=credentials)

    request = service.zones().list(project=project)
    while request is not None:
        response = request.execute()

        for zone in response['items']:
            # TODO: Change code below to process each `zone` resource:
            zones.append(zone['name'])

        request = service.zones().list_next(previous_request=request, previous_response=response)

    return zones


def get_instances(project_id, zone, api_version='v1'):
    instances = []

    credentials = GoogleCredentials.get_application_default()

    service = discovery.build('compute', api_version, credentials=credentials)
    # pylint: disable=no-member
    request = service.instances().list(project=project_id, zone=zone)

    while request is not None:
        try:
            response = request.execute()
        except:
            break

        if 'items' in response:
            for instance in response['items']:
                instances.append(instance)

        # pylint: disable=no-member
        request = service.instances().list_next(previous_request=request,
                                                previous_response=response)

    return instances


def get_hostvars(instance):
    hostvars = {
        'gce_id': instance['id'],
        'gce_status': instance['status']
    }

    if instance['networkInterfaces'] and instance['networkInterfaces'][0]['networkIP']:
        hostvars['ansible_ssh_host'] = instance['networkInterfaces'][0]['networkIP']

    if 'labels' in instance:
        hostvars['gce_labels'] = instance['labels']

    if 'items' in instance['metadata']:
        hostvars['gce_metadata'] = instance['metadata']['items']

    if 'items' in instance['tags']:
        hostvars['gce_tags'] = instance['tags']['items']

    return hostvars


def get_inventory(instances):
    inventory = collections.defaultdict(list)
    inventory['_meta'] = collections.defaultdict(
        lambda: collections.defaultdict(dict))

    for instance in instances:
        if instance['status'] in ['RUNNING', 'STAGING']:
            inventory['_meta']['hostvars'][instance['name']] \
                = get_hostvars(instance)

            # populate the 'all' group with all hosts found
            inventory['all'].append(instance['name'])

            # create a group for every tag prefixed by 'tag_' and populate
            # accordingly
            if 'items' in instance['tags']:
                for tag in instance['tags']['items']:
                    inventory['tag_{}'.format(tag)].append(instance['name'])

    return inventory


def main(args):
    project = args['--project']
    zone = args['--zone']
    api_version = args['--api-version']
    billing_account_name = args['--account']

    projects_list = []
    zones_list = []
    instances = []

    if project:
        projects_list.append(project)
    else:
        projects_list = get_all_billing_projects(billing_account_name)

    for project in projects_list:
        try:
            if zone:
                zones_list.append(zone)
            else:
                zones_list = get_all_zones_in_project(project)

            for zone in zones_list:
                for instance in get_instances(project_id=project,
                                  zone=zone,
                                  api_version=api_version):
                    instances.append(instance)
        except HttpError:
            continue

    inventory_json = get_inventory(instances)
    print(json.dumps(inventory_json,
                     sort_keys=True,
                     indent=2,
                     separators=(',', ': ')))

if __name__ == "__main__":
    log.basicConfig(filename='gce_googleapiclient.log')

    try:
        ARGS = docoptcfg(DOCOPT_USAGE,
                         config_option='--config',
                         env_prefix=ENV_PREFIX)
    except DocoptcfgFileError as exc:
        log.info('Failed reading: %s', str(exc))
        ARGS = docoptcfg(DOCOPT_USAGE, env_prefix=ENV_PREFIX)

    log.debug(ARGS)
    if not ARGS['--account']:
        print(DOCOPT_USAGE)
        exit(1)

    main(ARGS)
