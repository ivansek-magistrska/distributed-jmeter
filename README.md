## Distributed JMeter
Distributed JMeter application is a load generator application which was developed for master thesis project, but it can be used independently from master thesis project. For generating the load it uses the opensource software Apache JMeter. Distributed JMeter can be deployed on AWS or Google Cloud Platform. For more information how to do it, see below.

## Configs

Settings in config files are separated into sections for easier understanding.

### Amazon Web Services

**[SHOWCASE]**

```autoscalable``` - It's value ```yes``` or ```no``` tells application if showcase is deployed in autoscalable mode. This is important for getting the data from AWS.
```host``` - The host name where showcase is deployed. Showcase must be deployed on ```/showcase-1-a``` path
```frontend_instances_id``` - The name of frontend instances of showcase. It is used for getting data from showcase instances.

**[SCENARIO]**

```num_threads``` - The number of threads that we want to simulate. One JMeter instance can handle 2000 VU.
```ips``` - IP addresses of instances to deploy JMeter on. Leave empty to not use this setting.
```jmeter_url``` - URL to JMeter distribution. You can download JMeter and modify it, upload it somewhere and replace existing URL with yours. Otherwise leave as it is.

**[AWS]**

```region``` - The region name where to deploy application.
```aws_access_key_id``` - Your AWS access key.
```aws_secret_access_key``` - Your AWS secret key.
```availability_zones``` - Availability zones for region.

**[EC2]**

```instance_type``` - EC2 instance type for distributed JMeter
```remote_user``` - Virtual Machine user name for SSH access
```ami_id``` - Amazon Machine Image ID to provision VM from.
```key_name``` - Only the name of SSH key for connecting to VM.
```key_pair``` - Path to SSH key for connecting to VM. It is auto-generated.

**[RDS]**

```identifiers``` - Name of VM for RDS database.

### Google Cloud Platform

**[SHOWCASE]**

```host``` - The host name where showcase is deployed. Showcase must be deployed on ```/showcase-1-a``` path
```autoscalable``` - Value 'yes' or 'no' tells distributed JMeter application if showcase is deployed with autoscaling or without autoscaling.
```database_identifiers``` - The name of database identifier. If database is deployed in master-slave mode, the value is the name of all database identifiers separated by comma.

**[CREDENTIALS]**
```client_email``` - Client email value from Google Cloud Platform
```p12_path``` - Path to p12 certificate used for connecting to Google Cloud Platform

**[SCENARIO]**

```num_threads``` - The number of threads that we want to simulate. One JMeter instance can handle 2000 VU.
```duration_in_minutes``` - Duration of scenario in minutes

**[INSTANCES]**

```project``` - Project id on Google Cloud Platform
```zone``` - Zone in which the showcase is deployed
```image``` - Name of the image used to create instances from
```instance_type``` - Instance type used for running one JMeter instance. 
```public_key_path``` - Path to public key used for SSH access to instance.
```private_key_path``` - Path to private key used for SSH access to instance. 
```remote_user``` - Username for SSH access to the instance.
```frontend_instances_identifiers``` - Names of frontend instances if showcase is deployed without autoscaling, otherwise value is the prefix of the instances, e.g. 'cloudscale'.

## Installation

Before you can use distributed JMeter scripts you need to install them. You can do this by downloading the ZIP archive and then run:

```
$ python setup.py install 
```

You can also install the scripts using ```pip``` tool:

```
$ pip install -e https://github.com/ivansek-magistrska/distributed-jmeter/zipball/distributed-jmeter
```

## Usage

### Amazon Web Services
To run distributed JMeter on AWS edit ```bin/config.aws.ini``` file and run:

```
$ python run.py aws config.aws.ini scenarios/cloudscale-max.jmx
```

from ```bin/``` directory.

### Google Cloud Platform

To run distributed JMeter on Google Cloud Platform edit ```bin/config.google.ini``` file and run:

```
$ python run.py google config.google.ini scenarios/cloudscale-max.jmx
```

from ```bin/``` directory.
