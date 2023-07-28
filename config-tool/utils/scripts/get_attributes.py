import json

with open("/home/jonathan/Desktop/config-tool/pkg/lib/testdata/quay-config-schema.json") as infile:
    config = json.load(infile)

    attributes = []

    for prop_name in config['properties'].keys():
        attributes.append(prop_name)

    with open("/home/jonathan/Desktop/config-tool/attributes.txt","w") as outfile:

        for prop_name in attributes:

            outfile.write(prop_name+"\n")