# Transmitter

Middleware for REDCap and other systems to support clinical research data
integrations.

This software was developed to facilitate _All of Us_ Research Program efforts
at Weill Cornell Medicine. All of Us is a national program designed to gather
data from one million or more people living in the United States to accelerate
research and improve health. More information here: https://allofus.nih.gov.

## Approach and Concepts

### Handlers

*A handler is a function that receives a request-shaped map, and returns a
response-shaped map.*

It's assumed that a study is associated with one (but possibly more, if
dev/test/production versions exist) REDCap projects (or other upstream
unit/component). For each upstream project, there is a single URL endpoint; in
turn, that endpoint is handled by a handler function.

**Setting up routes** — the set of routes (endpoints and handler functions for them) can be configured in `main.py`.

**Mapping REDCap projects to handlers** — Two options:

* 1-to-1: A single handler can be dedicated to a single REDCap project
* 1-to-many: A handler can be configured to handle messages from multiple REDCap projects. This can be done via the `compose_handler` pattern, which takes a REDCap environment string, a PID, and returns a handler function. See the `aou_handler` module.

#### Handler tags

In the case of REDCap projects, a handler tag is the combination of these two pieces of data:

* REDCap environment: a four-character string such as 'sand' or 'prod'
* the PID

E.g., 'sand2814'.

#### Handlers for testing and development

Use these handlers for testing and so forth. Both assume the request comes from REDCap; comment out REDCap-specific logic to use with other source systems.

* `stdout_handler.py` — Write the incoming request to stdout.
* `email_test_handler.py` — Send the contents of the request to an email address, and log the event.

### Workflows

*A workflow is a function that receives a request-shaped map, and returns another request-shaped map with zero, one, or more additional key-value pairs inserted.*

The bulk of work happens in workflow modules (a handler is mostly a wrapper for workflows):

* receives a data baton (a request-shaped map);
* does work;
* returns that same baton, potentially with new key-value pairs added.

### Workflow chains

You can run a chain of workflows conveniently using the `run_workflow_chain` function in the `common` module.

#### Short-circuit a workflow chain

Short-circuit a workflow chain to end it early. To take advantage of short-circuiting, use the `run_workflow_chain` function.

If a workflow returns a map that contains the key `'done'` with the value `'yes'`, no subsequent workflows will be invoked. Instead, `'response'` will be retrieved (it should itself be a response-shaped map) from the map and returned.

**Example use case:** when REDCap sends an empty message to 'test' a new DET endpoint (which can be done in the project configuration), the `redcap_intake_workflow` decides that no further work is needed, and no other workflows are carried out.

### Data storage 

`datastore.py` provides an API for for simple key-value-like storage in MySQL.
It also timestamps each entry so that longitudinal versioning can be maintained
for any particular key.

## Requirements

* Python 2.7
* pip
* virtualenv
* MySQL database

## Deployment and configuration

### MySQL

Create the `datastore` table using `sql/create-datastore-table.sql`.

### Application folders

Create runtime and staging folders.

~~~
mkdir transmitter-staging
mkdir transmitter # or transmitter-test
~~~

In the `transmitter` folder, which is where the application will live and will be the working directory for the process, create the enclave folder, which is where all configuration files will live:

~~~
cd transmitter
mkdir enclave
~~~

(Note: in this README file, the directory name 'transmitter' is used; the included shell scripts use the directory names 'transmitter-prod' and 'transmitter-test' along with similarly named staging directories.)

### enclave/transmitter-config.json

This should be a JSON file with the following structure:

~~~
{"path-to-key": "/home/pki/private.key"
,"path-to-pem": "/home/pki/public.pem"
,"port": 2814
,"db-spec":
  { "host" : "localhost"
  , "user" : "X"
  , "password" : "X"
  , "db" : "nihpmi"
  , "charset" : "utf8mb4"
  }
}
~~~

* `"path-to-key"` can be `null` if your .pem file contains all public and private items.


### Handler-specific configuration

Each study should have its own configuration file.


#### enclave/aou-config.json

For the _All of Us_ Research Program, the configuration file is named `aou-config.json` file, which is required and should live in `enclave`.

~~~
{"study-details":
  {"pi": "X"
  ,"protocol-number":"X"
  }
,
"allowed-ips": ["X","X"]
,
"handler-tag-to-env-tag":
  {"prod2911": "test"
  ,"prod2525": "prod"}
,
"test":
  {"redcap-spec":
    {"api-url": "https://server:port/redcap_protocols/api/" 
    ,"token": "X"
    ,"username":"X"}
  ,"from-email":""
  ,"to-email": "X"
  }
,"prod":
  {"redcap-spec":
    {"api-url": "https://server:port/redcap_protocols/api/"
    ,"token": "X"
    ,"username":"X"}
  ,"from-email":""
  ,"to-email": "X"
  }
}
~~~

Customize the configuration values to suit. 

* The primary email address is for sending notifications of errors (though that might expand in the future).
* The "allowed-ips" list should contain IP addresses, e.g., of REDCap servers.

#### enclave/aou-api-config.json

This configuration file is needed when using the `wf_aou_confirm_affiliation` module.
This module connects to the AoU Data Ops API. See the aoulib documentation for more
details: https://github.com/wcmc-research-informatics/aoulib

### virtualenv

Create a virtualenv for the process to run in; run:

    mkdir venv
    virtualenv -p python2 venv

You might need to pass different arguments to virtualenv for your specific environment.

### Deploying code and dependencies

From the `transmitter-staging` folder, run:

~~~
git clone https://github.com/wcmc-research-informatics/transmitter .
~~~

Edit the `deploy.sh` script so that the directories you created the paths used
in the script. (You might find it necessary to make additional edits to suit your environment.)

Then activate the virtualenv and run the deploy script from your staging
directory (the script retrieves
dependencies and then copy files over from the staging folder into the live
`transmitter` folder) -- pass one of 'local', 'test', or 'prod' as the argument to deploy.sh. If 'local', 

~~~
source ../transmitter/venv/bin/activate
./deploy.sh test
~~~

For 'local', it will use the environment variable `TRANSMITTER_LOCAL_DEPLOY_DIR` as the destination. You can create an environment variable by adding this to .bash_profile:

    export TRANSMITTER_LOCAL_DEPLOY_DIR="/path/to/transmitter-local"

### Starting the process

Ensure you're inside the virtualenv, then start:

~~~
cd ../transmitter-test
./starttest.sh
# ...or...
cd ../transmitter
./startprod.sh
~~~

You can also configure the process as a daemon; the exact method varies depending on the Linux distro you're using.

## Updating your installation

To pull in the latest version, use the steps detailed in **Deploying code and dependencies** above, but replace the `git clone ...` command with simply the following (again, run this from the `transmitter-staging` folder:

~~~
git pull
~~~

## Migrating an installation from one server to another

The process is the same as deploying to a new server, with one additional task:
you'll need to migrate the data in the database to your new server. One method
is to export the data as a CSV from the old database, and then import into the
new one.

Export into a CSV:

    select * 
    from datastore 
    into outfile '/tmp/transmitter.csv' 
    fields terminated by ',' 
    enclosed by '"' lines 
    terminated by '\n';

Load into a table from a csv:

    load data local infile 'transmitter.csv' 
    into table datastore 
    fields terminated by ','  
    enclosed by '"' lines 
    terminated by '\n';

Note that the 'local' keyword might or might not be necessary.


## Logging

Logs are written to the `log` folder. The logging process is self-cleaning over time. The log folder is created automatically if it doesn't already exist.

