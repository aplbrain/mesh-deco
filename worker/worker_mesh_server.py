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
Python server to run meshing (marching-cubes) on annotation data.
"""

from base64 import b64encode
from flask import Flask, request, Response
from flask.json import jsonify
import numpy as np
from skimage import measure
from sys import argv


App = Flask(__name__)


def convert_to_obj(vert, tri):
    """
    Convert verts and faces to an OBJ file.

    Arguments:
        vert (int[]): List of verts
        tri (int[]): List of faces
    """
    res = ""
    for vert in vert:
        res += ("v {} {} {}\n".format(vert[0], vert[1], vert[2]))
    for face in tri:
        res += ("f {} {} {}\n".format(*(face + 1)))
    return res


def expand_tri(vert, tri):
    get_x = np.vectorize(lambda ix: vert[ix, 0])
    get_y = np.vectorize(lambda ix: vert[ix, 1])
    get_z = np.vectorize(lambda ix: vert[ix, 2])
    return np.stack([
        get_x(tri),
        get_y(tri),
        get_z(tri)], axis=-1)


@App.route("/mesh/generate/", methods=["POST"])
def generate_mesh():
    data = request.form
    dtype_ = data["dtype"]
    shape_ = tuple(map(int, data["shape"].split("|")))
    bytes_ = data["bytes"]
    offset_ = tuple(map(int, data["offset"].split("|")))
    mask_array = np.fromstring(bytes_, dtype=dtype_).reshape(shape_)
    # assumes a mask array arranged as x, y, z
    vert, tri, normals, values = measure.marching_cubes_lewiner(mask_array, 0)
    if tri.shape[0] > 0:
        vert += np.array(offset_).reshape((-1, 3))
        vert = vert.astype("float32")
        tri = np.apply_along_axis(
	        lambda row: np.roll(row, -1*row.argmin()),
	        1,
	        tri)
        tri = tri.astype("uint32")
        tri_of_vert = np.unique(expand_tri(vert, tri), axis=0)
    else:
        tri_of_vert = np.empty((0, 0, 0))
    rtn = dict()
    rtn["dtype"] = str(tri_of_vert.dtype)
    rtn["shape"] = "|".join(map(str, tri_of_vert.shape))
    rtn["bytes"] = b64encode(tri_of_vert.ravel().tostring()).decode("utf-8")
    return jsonify(rtn)


@App.route("/")
def hello():
    """Root."""
    return "Welcome to the Mesh Worker Node!"


if __name__ == "__main__":
    App.run()
