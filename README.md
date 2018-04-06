# mesh-deco

Set of tools for meshing annotated blocks of data
using a master server and a family of workers.


## Installation
Clone the repository into a designated local parent directory. Navigate into the directory and construct virtual environments (using either virtualenv or conda) for each of the master and worker nodes.

For each node type (master and worker), navigate into the directory, and use the type-specific requirements.txt file to install the node dependencies.

## Running
You will need to define a JSON-formatted configuration file, launch your worker nodes, and then launch your master node.

#### The Config
You will need to construct a config file to point your master to your workers in a list format. The data for the config need only specify the endpoints, allowing for local, remote, or serverless resources to be used. The config object is very simple, containing a single top-level "workers" key which houses a list of objects that each contain the "url" key leading to a particular worker endpoint. The worker endpoint can be found at /mesh/generate/.

A simple local example of a config is as follows.

{
    "workers": [
        {
            "url": "http://localhost:5001/mesh/generate/"
        },
        {
            "url": "http://localhost:5002/mesh/generate/"
        },
        {
            "url": "http://localhost:5003/mesh/generate/"
        },
        {
            "url": "http://localhost:5004/mesh/generate/"
        }
    ]
}

#### Workers on Servers
To launch the worker nodes on servers, simply log into the server, clone the repo, create the worker virtual environment with the required dependencies, and then call `python worker_mesh_server.py <port-number>`. If you have a particularly large number of servers, the pssh command should be useful.

#### Workers on AWS Lambda

#### Master Node
To launch the master, load the master virtual environment and then (from within the master directory) call `python master_mesh_server.py /path/to/config/file`. The master will assign meshing jobs to workers cyclically based on the order specified in the config. At present, the master exposes two endpoints: /mesh/file/ and /mesh/janelia/. The /mesh/file/ endpoint accepts binary mask data encoded as a numpy array saved using np.save. The /mesh/janelia/ endpoint accepts data in the form of binary blocks as specified in Janelia's block streaming format.

## License
Copyright 2018 The Johns Hopkins University Applied Physics Laboratory.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Legal

Use or redistribution of this system in source and/or binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code or binary forms must adhere to the terms and conditions of any applicable software licenses.
2. End-user documentation or notices, whether included as part of a redistribution or disseminated as part of a legal or scientific disclosure (e.g. publication) or advertisement, must include the following acknowledgement:  The Boss software system was designed and developed by the Johns Hopkins University Applied Physics Laboratory (JHU/APL).
3. The names "The Boss", "JHU/APL", "Johns Hopkins University", "Applied Physics Laboratory", "MICrONS", or "IARPA" must not be used to endorse or promote products derived from this software without prior written permission. For written permission, please contact BossAdmin@jhuapl.edu.
4. This source code and library is distributed in the hope that it will be useful, but is provided without any warranty of any kind.
