from app import userfiles as user_files

import workers.dockerfilebuild
import requests

w = workers.dockerfilebuild.DockerfileBuildWorker(100, None)

resource_key = "5c0a985c-405d-4161-b0ac-603c3757b5f9"
resource_url = user_files.get_file_url(resource_key, "127.0.0.1", requires_cors=False)
print(resource_url)

docker_resource = requests.get(resource_url, stream=True)
c_type = docker_resource.headers["content-type"]

if ";" in c_type:
    c_type = c_type.split(";")[0]

build_dir = w._mime_processors[c_type](docker_resource)
print(build_dir)
