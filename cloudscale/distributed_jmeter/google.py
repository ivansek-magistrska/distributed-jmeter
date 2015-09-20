from googleapiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
import traceback
import logging
import time
import datetime
import paramiko
import os
from cloudscale.distributed_jmeter.aws import AWS


class Config:
    pass

class Instance:
    def __init__(self, ip_address, id):
        self.ip_address = ip_address
        self.id = id

class Helpers:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger

    def _wait_for_operation(self, result, status='DONE'):
        if result['status'] == status:
            self.logger.log("done.")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        else:
            self.logger.log('.', append_to_last=True)
            time.sleep(1)

    def _wait_for_operation_global(self, compute, project, operation):
        self.logger.log('Waiting for operation to finish')
        while True:
            result = compute.globalOperations().get(
                    project=project,
                    operation=operation).execute()
            r = self._wait_for_operation(result)
            if not r is None:
                return r

    def _wait_for_operation_region(self, compute, project, operation, region):
        self.logger.log('Waiting for operation to finish')
        while True:
            result = compute.regionOperations().get(
                    project=project,
                    region=region,
                    operation=operation).execute()
            r = self._wait_for_operation(result)
            if not r is None:
                return r

    def _wait_for_operation_zone(self, compute, project, operation, zone):
        self.logger.log('Waiting for operation to finish')
        while True:
            result = compute.zoneOperations().get(
                    project=project,
                    zone=zone,
                    operation=operation).execute()
            r = self._wait_for_operation(result)
            if not r is None:
                return r

    def ssh_to_instance(self, ip_addr, user, key_pair, i=0):
        try:
            if i < 3:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                if key_pair:
                    ssh.connect(ip_addr, username=user, key_filename=os.path.abspath(key_pair))
                else:
                    ssh.connect(ip_addr, username=user, password="")
                return ssh
            raise Exception('Failed 3 times to SSH to %s' % ip_addr)
        except Exception as e:
            self.logger.log('%s\nTrying to reconnect ...' % e.message)
            time.sleep(30)
            return self.ssh_to_instance(ip_addr, i=i + 1)


class Google(AWS, Helpers):

    def __init__(self, cfg, scenario_path, r_path, output_path, logger, test=False):
        Helpers.__init__(self, cfg, logger)
        AWS.__init__(self, cfg, scenario_path, r_path, output_path, logger, test)

    def init(self):
        self.i = 0
        self.instances = []
        self.config = Config()
        self.config.client_email = self.cfg.get('CREDENTIALS', 'client_email')
        self.config.p12_path = self.cfg.get('CREDENTIALS', 'p12_path')
        self.config.project = self.cfg.get('INSTANCES', 'project')
        self.config.zone = self.cfg.get('INSTANCES', 'zone')
        self.config.image = self.cfg.get('INSTANCES', 'image')
        self.config.instance_type = self.cfg.get('INSTANCES', 'instance_type')
        self.config.public_key_path = self.cfg.get('INSTANCES', 'public_key_path')


        self.key_pair = self.cfg.get('INSTANCES', 'private_key_path')
        self.jmeter_url = self.cfg.get('JMETER', 'url')
        self.user = self.cfg.get('INSTANCES', 'remote_user')
        self.startup_threads = int(self.cfg.get('TEST', 'startup_threads'))
        self.rest_threads = int(self.cfg.get('TEST', 'rest_threads'))
        self.host = self.cfg.get('SHOWCASE', 'host')
        self.is_autoscalable = True if self.cfg.get('SHOWCASE', 'autoscalable') == 'yes' else False
        self.num_threads = int(self.cfg.get('SCENARIO', 'num_threads'))
        self.scenario_duration = int(self.cfg.get('SCENARIO', 'duration_in_minutes'))
        self.num_jmeter_slaves = int(self.cfg.get('TEST', 'num_jmeter_slaves'))
        self.frontend_instances_identifier = self.cfg.get('INSTANCES', 'frontend_instances_identifiers').split(',')
        self.rds_identifiers = self.cfg.get('SHOWCASE', 'database_identifiers')

        credentials = self.login()
        self.compute = build('compute', 'v1', credentials=credentials)
        self.monitoring = build('cloudmonitoring', 'v2beta2', credentials=credentials)

    def login(self):
        client_email = self.config.client_email
        with open(self.config.p12_path) as f:
            private_key = f.read()

        credentials = SignedJwtAssertionCredentials(client_email, private_key,
            'https://www.googleapis.com/auth/cloud-platform')
        return credentials

    def create_instance(self, msg):
        self.logger.log(msg)

        name = "jmeter-%s" % self.i

        project = self.config.project
        source_disk_image = "projects/%s/global/images/%s" % (self.config.project, self.config.image)
        machine_type = "zones/%s/machineTypes/%s" % (self.config.zone, self.config.instance_type)

        with open(self.config.public_key_path) as fp:
            public_key = fp.read()

        body = {
            'name': name,
            'machineType': machine_type,
            'tags': {
                'items': ['jmeter', 'http-server'],
            },

            # Specify the boot disk and the image to use as a source.
            'disks': [
                {
                    'boot': True,
                    'autoDelete': True,
                    'initializeParams': {
                        'sourceImage': source_disk_image,
                    }
                }
            ],

            # Specify a network interface with NAT to access the public
            # internet.
            'networkInterfaces': [{
                'network': 'global/networks/default',
                'accessConfigs': [
                    {'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}
                ]
            }],

            # Allow the instance to access cloud storage and logging.
            'serviceAccounts': [{
                'email': 'default',
                'scopes': [
                    'https://www.googleapis.com/auth/devstorage.read_write',
                    'https://www.googleapis.com/auth/logging.write'
                ]
            }],

            # Metadata is readable from the instance and allows you to
            # pass configuration from deployment scripts to instances.
            'metadata': {
                'items': [
                    {
                        'key': 'sshKeys',
                        'value': public_key
                    },
                {
                    # Every project has a default Cloud Storage bucket that's
                    # the same name as the project.
                    'key': 'bucket',
                    'value': project
                }]
            }
        }

        try:
            operation = self.compute.instances().insert(
                project=self.config.project,
                zone=self.config.zone,
                body=body
            ).execute()
            self._wait_for_operation_zone(self.compute, self.config.project, operation['name'], self.config.zone)
        except Exception as e:
            self.logger.log(traceback.format_exc().splitlines()[-1], level=logging.ERROR)

        operation = self.compute.instances().get(project=self.config.project, zone=self.config.zone, instance=name).execute()

        self.i=self.i+1
        instance = Instance(operation['networkInterfaces'][0]['accessConfigs'][0]['natIP'], name)
        self.instances.append(instance)
        return instance

    def terminate_instances(self, ips):
        pass

    def get_instances_by_tag(self, tag, value):
        instances = []
        if self.is_autoscalable:
            value=[]
            operation = self.compute.instances().list(project=self.config.project,
                                          zone=self.config.zone,
                                          filter='name eq %s.*' % self.frontend_instances_identifier).execute()
            for i in operation['items']:
                value.append(i['name'])

        for name in value:
            i = self.compute.instances().get(
                project=self.config.project,
                zone=self.config.zone,
                instance=name
            ).execute()
            instance = Instance(i['networkInterfaces'][0]['accessConfigs'][0]['natIP'], name)
            instances.append(instance)
        return instances

    def get_cloudwatch_ec2_data(self, start_time, end_time, instance_ids):
        oldest_time = end_time.isoformat('T') + 'Z'
        youngest_time = start_time.isoformat('T') + 'Z'
        data = []
        if self.is_autoscalable:
            instance_id = self.frontend_instances_identifier[0]
            d = self.monitoring.timeseries().list(
                project=self.config.project,
                metric='compute.googleapis.com/instance/cpu/utilization',
                youngest=oldest_time,
                oldest=youngest_time,
                labels='compute.googleapis.com/instance_name=~%s*.+' % instance_id
            ).execute()

            for i in xrange(len(d['timeseries'])):
                cpu_data = []
                instance_id = d['timeseries'][i]['timeseriesDesc']['labels']['compute.googleapis.com/instance_name']
                for point in d['timeseries'][i]['points']:
                    cpu_data.append({
                        'Timestamp': datetime.datetime.strptime(point['end'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                        'Average': point['doubleValue']
                    })

                data.append({
                    'instance_id': instance_id,
                    'data': cpu_data
                })
        else:
            for instance_id in instance_ids:
                d = self.monitoring.timeseries().list(
                    project=self.config.project,
                    metric='compute.googleapis.com/instance/cpu/utilization',
                    youngest=oldest_time,
                    oldest=youngest_time,
                    labels='compute.googleapis.com/instance_name==%s' % instance_id
                ).execute()

                cpu_data = []
                for point in d['timeseries'][0]['points']:
                    cpu_data.append({
                        'Timestamp': datetime.datetime.strptime(point['end'], '%Y-%m-%dT%H:%M:%S.%fZ'),
                        'Average': point['doubleValue']
                    })

                data.append({
                    'instance_id': instance_id,
                    'data': cpu_data
                })


        return data

    def get_cloudwatch_rds_data(self, start_time, end_time, instance_ids):
        return []

    def get_autoscalability_data(self, start_time, end_time):
        return []