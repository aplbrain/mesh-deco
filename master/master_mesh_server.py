"""
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
"""

"""
Python server to orchestrate meshing on annotation data.
"""

from base64 import b64decode
from deco import concurrent, synchronized
from flask import Flask, request, Response
from intern.remote.boss import BossRemote
from intern.resource.boss.resource import ChannelResource
from intern.utils.parallel import block_compute
from janelia_convert import assemble_array, assemble_list
import json
import logging
import numpy as np
from requests import codes, post
from sys import argv


boss = BossRemote()
App = Flask(__name__)
worker_config = json.load(open(argv[1], "r"))
worker_url_list = [
        worker["url"]
        for worker in worker_config["workers"]]


@App.route("/mesh/file/", methods=["POST"])
def mesh_from_file():
    """
    Return an OBJ from an uploaded numpy file

    Args:
        None
    """
    mask_array = np.logical_not(np.load(request.files["numpy"]))
    logging.info("array shape is ({}, {}, {})".format(
        mask_array.shape[0],
        mask_array.shape[1],
        mask_array.shape[2]))
    obj_str = distribute_requests(mask_array)
    return obj_str


@App.route("/mesh/janelia/", methods=["POST"])
def mesh_from_janelia():
    """
    Return an OBJ from an uploaded janelia binary file

    Args:
        None
    """
    body = request.files["janelia"]
    mask_list = assemble_list(body, granularity="subblock")
    logging.info("{} blocks in mask list".format(len(mask_list)))
    mask_array = assemble_array(mask_list)
    logging.info("array shape is ({}, {}, {})".format(
        mask_array.shape[0],
        mask_array.shape[1],
        mask_array.shape[2]))
    obj_str = distribute_requests(mask_array)
    return obj_str


@App.route("/mesh/boss/<col>/<exp>/<chan>/<res>/<x>:<X>/<y>:<Y>/<z>:<Z>/<id>/")
def mesh_from_boss(col, exp, chan, res, x, X, y, Y, z, Z, id):
    """
    Return the meshed volume as a .OBJ.

    Args:
        yes please
    """
    body = boss.get_cutout(
        ChannelResource(chan, col, exp, datatype="uint64"),
        res,
        [int(x), int(X)],
        [int(y), int(Y)],
        [int(z), int(Z)])
    mask_array = (body == int(id))
    logging.info("array shape is ({}, {}, {})".format(
        mask_array.shape[0],
        mask_array.shape[1],
        mask_array.shape[2]))
    obj_str = distribute_requests(mask_array)
    return obj_str


@concurrent
def send_mesh_request(worker_url, mask_array, offset):
    data = dict()
    shape = mask_array.shape
    if \
            (1 in shape) or \
            (np.sum(mask_array) == 0) or \
            (np.sum(mask_array) == shape[0]*shape[1]*shape[2]):
        tri_of_vert = np.empty((0, 0, 0))
    else:
        data["dtype"] = str(mask_array.dtype)
        data["shape"] = "|".join(map(str, shape))
        data["bytes"] = mask_array.ravel().tostring()
        data["offset"] = "|".join(map(str, offset))
        response = post(worker_url, data=data)
        if response.status_code != codes.ok:
            logging.error('status code {} from {}'.format(
                response.status_code,
                worker_url))
            tri_of_vert = np.empty((0, 0, 0))
        else:
            rtn = json.loads(response.text)
            dtype_ = rtn["dtype"]
            shape_ = tuple(map(int, rtn["shape"].split("|")))
            bytes_ = str.encode(rtn["bytes"])
            tri_of_vert = np.fromstring(
                    b64decode(bytes_),
                    dtype=dtype_).reshape(shape_)
    return tri_of_vert


@synchronized
def distribute_requests_helper(mask_array, block_size=(64, 64, 64)):
    """
    Partition the mask array into blocks with
    fixed shape and send processing requests
    to worker nodes.

    Args:
        mask_array: binary-valued 3-d numpy array
        block_size: dimensions of blocks

    Return:
        coregistered lists of vertices and triangular
        faces from worker nodes
    """
    obj_dict = dict()
    x_start, y_start, z_start = (0, 0, 0)
    x_stop, y_stop, z_stop = mask_array.shape
    index_list = block_compute(
            x_start, x_stop,
            y_start, y_stop,
            z_start, z_stop,
            block_size=block_size)
    n_workers = len(worker_url_list)
    for w_ix, index in enumerate(index_list):
        x_bounds, y_bounds, z_bounds = index
        # adding 1 to index to make bounds inclusive;
        # this means we draw the same face twice
        # for when we merge
        wrapped_ix = w_ix % n_workers
        worker_url = worker_url_list[wrapped_ix]
        block = mask_array[
                x_bounds[0]:(x_bounds[1]+1),
                y_bounds[0]:(y_bounds[1]+1),
                z_bounds[0]:(z_bounds[1]+1)]
        offset = (
                x_bounds[0],
                y_bounds[0],
                z_bounds[0])
        obj_dict[index] = send_mesh_request(
                worker_url,
                block,
                offset)
    logging.info("Finished submitting requests to workers...")
    return obj_dict


def distribute_requests(mask_array, block_size=(64, 64, 64)):
    obj_dict = distribute_requests_helper(mask_array, block_size)
    # assemble .OBJ strings
    t_of_v_list = list()
    for key in obj_dict:
        t_of_v = obj_dict[key]
        if t_of_v.shape != (0, 0, 0):
            t_of_v_list.append(t_of_v)
    logging.info("Collected OBJs from workers...")
    logging.info("Reassembling OBJs from list...")
    obj_str = reassemble_obj(t_of_v_list)
    logging.info("Finished OBJ reassembly!")
    return obj_str


def reassemble_obj(t_of_v_list):
    """
    Recompile coregistered lists of vertices and
    triangular faces from worker nodes into a single
    .OBJ file representing the meshed version of the
    object indicted by the original mask array.

    Args:
        vert_list: list of vertex arrays
        tri_list: list of triangular face arrays

    Return:
        string representing compiled .OBJ file
    """
    # simplify joined face list
    tri_of_vert = np.unique(np.concatenate(
        t_of_v_list,
        axis=0), axis=0)
    # simplify vertex list
    # assume C ordering
    vert = np.unique(
            tri_of_vert.reshape((-1, 3)),
            axis=0)
    # populate vertex lookup
    counter = 1
    lookup = dict()
    v_list = []
    for v in vert:
        key = tuple(v)
        if key not in lookup:
            lookup[key] = counter
            v_list.append("v {} {} {}".format(*key))
            counter = counter + 1
    # populate face list
    n_tri = tri_of_vert.shape[0]
    t_list = []
    for t_ix in range(n_tri):
        key0 = tuple(tri_of_vert[t_ix, 0, :])
        key1 = tuple(tri_of_vert[t_ix, 1, :])
        key2 = tuple(tri_of_vert[t_ix, 2, :])
        t_list.append("f {} {} {}".format(
            lookup[key0],
            lookup[key1],
            lookup[key2]))
    obj_str = "\n".join(v_list) + "\n" + "\n".join(t_list)
    return obj_str


@App.route("/")
def hello():
    """Root."""
    return "Welcome to the Mesh Master Node!"


if __name__ == "__main__":
    App.run(port=5000)
