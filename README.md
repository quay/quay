# Quay Config Validation Tool

This tool is used to validate configuration bundles for use with Quay. 

## Installation

Use the `go get` command to install config-tool.

```bash
go get -u github.com/quay/config-tool/config-tool
```

## Design
This tool can be used as either a library or through the command line. 

```
config-tool/
├── cmd
│   └── config-tool
│       └── main.go
├── commands # This is where the Cobra CLI commands are called from
│   ├── root.go
│   └── validate.go
├── go.mod
├── go.sum
├── LICENSE
├── pkg
│   └── lib # This folder contains the public library that can be imported
│       ├── testdata
│       │   ├── config1.yaml
│       │   ├── config2.yaml
│       │   └── quay-config-schema.json
│       ├── validate.go
│       └── validate_test.go
├── README.md
└── utils # This folder contains tools and scripts used in development
    └── dumpschema.py
```

## CLI Usage

```
Usage:
  config-tool validate [flags]

Flags:
  -c, --configPath string   The path to a config file
  -h, --help                help for validate
  -s, --schemaPath string   The path to a schema JSON file
```

## Library
The library contains functions that can be imported into other Go projects. 

## License
[Apache 2.0](https://choosealicense.com/licenses/apache-2.0/)