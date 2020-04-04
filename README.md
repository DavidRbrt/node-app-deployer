# node-app-deployer

## Prerequisites

- you may need to install python packages:

> pip<version> install gitpython

- you need to have your repo cloned with enabled credentials:

> git clone <url/project>

> mkdir <project>

> git config credential.helper store

> git pull

- app server port as to be open:

> sudo ufw allow <port>

## Run on target

> ./deploy-node-app --help