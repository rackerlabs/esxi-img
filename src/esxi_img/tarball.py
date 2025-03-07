# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import tarfile
from pathlib import Path


class Tarball:
    """Abstraction to ensure we create valid tarballs for ESXi.

    Provides an abstraction to adding files and ensuring we set
    all the necessary flags and options to generate a tarball that
    ESXi will accept.
    """

    def __init__(self) -> None:
        self._paths: set[Path] = set()
        self._files: dict[Path, Path | str | None] = dict()

    def _add_path_walk(self, path: Path) -> None:
        """Walks the path up the parents to ensure they're all present."""
        stop_path = Path(".")
        while path != stop_path:
            # add the current path
            self._paths.add(path)
            # and now do the parent
            path = path.parent

    def add_file(self, path: Path, file: Path) -> None:
        # we need to walk the path and ensure all the parents are added as well
        self._add_path_walk(path)
        self._files[path] = file

    def add_text(self, path: Path, data: str) -> None:
        self._add_path_walk(path)
        self._files[path] = data

    def iter_files(self):
        # sort the paths so they come out correctly
        paths = sorted(self._paths)

        for path in paths:
            try:
                yield (path, tarfile.REGTYPE, self._files[path])
            except KeyError:
                yield (path, tarfile.DIRTYPE, None)
