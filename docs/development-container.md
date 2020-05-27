# Quay Development Container

The instructions below describe how to create and setup a container for working with local source changes and testing. It is meant for a developer familiar with python, javascript, and the tools associated with development.

## Quay Source

For convenience, the environment variable `QUAY_DEVEL_HOME` will be referenced for locations of the parent directory for source and other directories.

The directory `$QUAY_DEVEL_HOME/quay` is your _development_ git checkout of [quay](https://github.com/quay/quay).
```
cd $QUAY_DEVEL_HOME
git checkout github.com/quay/quay.git
```

For local storage, create the directory where images will be written to disk.
```
cd $QUAY_DEVEL_HOME
mkdir quay-storage
```

The Quay config app should be previously run and the resulting _quay-config.tar.gz_ expanded into place. This file is copied into this directory for convenience only: Keeping it available will allow upload into the config app for modifications later.
```
cd $QUAY_DEVEL_HOME
mkdir quay-config
cp ~/Downloads/quay-config.tar.gz $QUAY_DEVEL_HOME/quay-config/quay-config.tar.gz
tar xvf $QUAY_DEVEL_HOME/quay-config/quay-config.tar.gz -C $QUAY_DEVEL_HOME/quay-config
```

## Building Development Container

Build an image in a clean git checkout of master branch. It's important not to do this in your own development directory as there may be files that conflict or break a clean build.
```
cd $QUAY_DEVEL_HOME/quay
docker build -t quay:devel -f Dockerfile .
```

## Run Development Container

Note: Assumptions are that the config app has successfully run and database is available. This can be done via regular user documentation and using the `quay:devel` image built above.

```
docker run --rm --name quay \
    -v $QUAY_DEVEL_HOME/quay-config:/conf/stack \
    -v $QUAY_DEVEL_HOME/quay-storage:/datastorage \
    -v $QUAY_DEVEL_HOME/quay:$QUAY_DEVEL_HOME/quay \
    -p 8080:8080 \
    -p 8443:8443 \
    -p 9092:9092 \
    -e QUAY_DEVEL_HOME=$QUAY_DEVEL_HOME \
    quay:devel
```

This will start the quay container and be fully running. The web UI is available at port 8443.

## Switch Services to Development

### Inside the Container

When exec'ing into the development container, it is best to run under the [SCLs](https://www.softwarecollections.org) used during production. This will provide the correct paths to python and other executables.

```
docker exec --rm -it quay bash
```

The following sections are perhaps easiest to run in separate `docker exec` sessions, which is how they will be described. Some or all could be run in the background and managed differently than described here.

### Stop Services

When running the quay container, all regular services are started by default. In order to run a service locally, stopping the default is important. Below are the steps for developing the web UI and web backend python service.

Stop services:
```
supervisorctl -c /quay-registry/conf/supervisord.conf stop gunicorn-web
```

Change the web resources to devel location:
```
cd /quay-registry
mv static static.bak
ln -s $QUAY_DEVEL_HOME/quay/static
```

Build web assets:
```
cd $QUAY_DEVEL_HOME/quay
mkdir -p static/webfonts
mkdir -p static/fonts
mkdir -p static/ldn
PYTHONPATH=. python -m external_libraries

yarn build
```

### Run Migrations

If `$QUAY_DEVEL_HOME/quay`, which presumably has your local code changes, has migrations, special care should be taken when switching between different versions of code.

To run a migration:
```
cd $QUAY_DEVEL_HOME/quay
PYTHONPATH=. alembic upgrade 5248ddf35167
```

To revert a migration:
```
cd $QUAY_DEVEL_HOME/quay
PYTHONPATH=. alembic downgrade -1
```

### Web UI Assets

```
cd $QUAY_DEVEL_HOME/quay
yarn build && npm run watch
```

### Run Web Server
```
cd $QUAY_DEVEL_HOME/quay
PYTHONPATH=. gunicorn -c conf/gunicorn_web.py web:application
```
