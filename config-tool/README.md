# Config Tool

The Quay Config Tool implements several features to capture and validate configuration data based on a predefined schema.

This tool includes the following features:

- Validate Quay configuration using CLI tool
- Generate code for custom field group definitions (includes structs, constructors, defaults)
- Validation tag support from [Validator](https://github.com/go-playground/validator)
- Built-in validator tags for OAuth and JWT structs

## Installation

### Build from Source

Install using the Go tool:

```
go get -u github.com/quay/quay/config-tool/...
```

This will generate files for the Quay validator executable and install the `config-tool` CLI tool.

### Build from Dockerfile

Clone this repo and build an image:

```
$ git clone https://github.com/quay/quay.git
$ cd quay/config-tool
$ sudo podman build -t config-tool .
```

Start the container and execute command:

```
$ sudo podman run -it -v ${CONFIG_MOUNT}:/conf config-tool ...
```

Note that you must mount in your config directory in order for the config-tool to see it.

#### Note: By default, this tool will generate an executable from a pre-built Config definition. For usage on writing a custom Config definition see [here](https://github.com/quay/quay/tree/master/config-tool/utils/generate)

## Usage

The CLI tool contains two main commands:

#### The `print` command is used to output the entire configuration with defaults specified

```
{
        "HostSettings": (*fieldgroups.HostSettingsFieldGroup)({
                ServerHostname: "quay:8081",
                PreferredURLScheme: "https",
                ExternalTLSTermination: false
        }),
        "TagExpiration": (*fieldgroups.TagExpirationFieldGroup)({
                FeatureChangeTagExpiration: false,
                DefaultTagExpiration: "2w",
                TagExpirationOptions: {
                        "0s",
                        "1d",
                        "1w",
                        "2w",
                        "4w"
                }
        }),
        "UserVisibleSettings": (*fieldgroups.UserVisibleSettingsFieldGroup)({
                RegistryTitle: "Project Quay",
                RegistryTitleShort: "Project Quay",
                SearchResultsPerPage: 10,
                SearchMaxResultPageCount: 10,
                ContactInfo: {
                },
                AvatarKind: "local",
                Branding: (*fieldgroups.BrandingStruct)({
                        Logo: "not_a_url",
                        FooterIMG: "also_not_a_url",
                        FooterURL: ""
                })
        })
}
```

#### The `validate` command is used to show while field groups have been validated succesully

```
$ config-tool validate -c <path-to-config-dir>
+---------------------+--------------------+-------------------------+--------+
|     FIELD GROUP     |       FIELD        |          ERROR          | STATUS |
+---------------------+--------------------+-------------------------+--------+
| HostSettings        | -                  | -                       | 🟢     |
| TagExpiration       | -                  | -                       | 🟢     |
| UserVisibleSettings | BRANDING.Logo      | Field enforces tag: url | 🔴     |
|                     | BRANDING.FooterIMG | Field enforces tag: url | 🔴     |
+---------------------+--------------------+-------------------------+--------+
```

#### The `editor` command will bring up an interactive UI to reconfigure and validate a config bundle.

```
$ config-tool editor -c <path-to-config-dir> -p <editor-password> -e <operator-endpoint>
```

This command will bring up an interactive UI in which a user can modify, validate, and download a config. In addition, Swagger documentation can be reached by going to `{{host}}/swagger/index.html`

### Using HTTPS

You can deploy the config editor using TLS certificates by passing environment variables to the runtime. The public and private keys must contain valid SANs for the route that you wish to deploy the editor on.

The paths can be specifed using `CONFIG_TOOL_PRIVATE_KEY` and `CONFIG_TOOL_PUBLIC_KEY`.

NOTE: If running from a container, the `CONFIG_TOOL_PRIVATE_KEY` and `CONFIG_TOOL_PUBLIC_KEY` values are the locations of the certs INSIDE the container. This might look something like the following:

```
$ docker run -p 7070:8080 \

-v ${PRIVATE_KEY_PATH}:/tls/localhost.key \
-v ${PUBLIC_KEY_PATH}:/tls/localhost.crt \
-e CONFIG_TOOL_PRIVATE_KEY=/tls/localhost.key \
-e CONFIG_TOOL_PUBLIC_KEY=/tls/localhost.crt \
-e DEBUGLOG=true \
-ti config-app:dev
```
