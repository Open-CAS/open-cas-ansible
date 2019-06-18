#
# Copyright(c) 2012-2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import os
import csv

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleError
from ansible.utils.vars import merge_hash


def validate_ioclass_file(ioclass_file):
    if ioclass_file is None:
        return

    file_path = "roles/opencas-deploy/files/{0}".format(ioclass_file)
    if not os.path.exists(file_path):
        raise AnsibleError(
            "{0} io class file wasn't found in opencas-deploy files".format(
                ioclass_file
            )
        )

    with open(file_path, "r") as f:
        reader = csv.DictReader(f, restkey="unnamed fields")

        required = set(
            ["IO class id", "IO class name", "Eviction priority", "Allocation"]
        )
        if set(reader.fieldnames) != required:
            raise AnsibleError(
                "Invalid IO-class file format ({0})".format(ioclass_file)
            )

        ioclass_ids = []
        for ioclass in reader:
            if "unnamed fields" in ioclass:
                raise AnsibleError(
                    "Invalid IO-class file format ({0})".format(ioclass_file)
                )

            try:
                id = int(ioclass["IO class id"])
            except:
                raise AnsibleError(
                    "Invalid IO-class id({0}) found in {1}".format(
                        ioclass["IO class id"], ioclass_file
                    )
                )

            if not (0 <= id < 33):
                raise AnsibleError(
                    "Invalid IO-class id({0}) found in {1}".format(
                        id, ioclass_file
                    )
                )

            if id in ioclass_ids:
                raise AnsibleError(
                    "Duplicate IO-class id({0}) found in {1}".format(
                        id, ioclass_file
                    )
                )
            ioclass_ids += [id]

            try:
                name = str(ioclass["IO class name"])
            except:
                raise AnsibleError(
                    "Invalid IO-class name({0}) found in {1}".format(
                        ioclass["IO class name"], ioclass_file
                    )
                )

            if len(name) >= 1024:
                raise AnsibleError(
                    "Too long IO-class name({0}) found in {1}".format(
                        name, ioclass_file
                    )
                )

            for c in name:
                if c == "," or c == '"' or ord(c) < 32 or ord(c) > 126:
                    raise AnsibleError(
                        "Invalid character({0}) in IO-class name({1}) found in {2}".format(
                            c, name, ioclass_file
                        )
                    )

            try:
                priority = int(ioclass["Eviction priority"])
            except:
                raise AnsibleError(
                    "Invalid IO-class priority({0}) found in {1}".format(
                        ioclass["IO class id"], ioclass_file
                    )
                )

            if not (0 <= priority <= 255):
                raise AnsibleError(
                    "Out of range IO-class priority({0}) found in {1}".format(
                        priority, ioclass_file
                    )
                )

            try:
                allocation = int(ioclass["Allocation"])
            except:
                raise AnsibleError(
                    "Invalid IO-class allocation({0}) found in {1}".format(
                        ioclass["Allocation"], ioclass_file
                    )
                )

            if not (0 <= allocation <= 1):
                raise AnsibleError(
                    "Invalid IO-class allocation({0}) found in {1}".format(
                        allocation, ioclass_file
                    )
                )


class ActionModule(ActionBase):
    def run(self, tmp=None, task_vars=None):
        if (
            "check_cache_config" in self._task.args
            and "io_class" in self._task.args["check_cache_config"]
            and self._task.args["check_cache_config"]["io_class"]
        ):
            validate_ioclass_file(
                self._task.args["check_cache_config"]["io_class"]
            )
            del self._task.args["check_cache_config"]["io_class"]

        results = super(ActionModule, self).run(tmp, task_vars)
        results = merge_hash(
            results, self._execute_module(tmp=tmp, task_vars=task_vars)
        )

        return results
