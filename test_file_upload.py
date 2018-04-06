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
Python script to test file upload.
"""

import numpy as np
from requests import post


if __name__ == "__main__":
    file_name = "test.npy"
    file_handle = open(file_name, "rb")
    files = {
            "numpy": (
                file_name,
                file_handle)}
    response = post(
            "http://127.0.0.1:5000/mesh/file/",
            files=files)
    obj = response.text
    print(obj)
