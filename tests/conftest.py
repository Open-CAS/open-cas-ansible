#
# Copyright(c) 2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#


import sys
import os


def pytest_configure(config):
    sys.path.append(
        os.path.join(os.path.dirname(__file__), "open-cas-linux/utils/")
    )
    sys.path.append(os.path.join(os.path.dirname(__file__), "../library"))
