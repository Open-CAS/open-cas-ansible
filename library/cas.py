#
# Copyright(c) 2012-2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause
#

import sys
from copy import deepcopy

try:
    sys.path.append("/usr/lib/opencas/")
    import opencas as cas_util
except ImportError:
    cas_util = None

ANSIBLE_METADATA = {
    "metadata_version": "0.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = """
---
module: cas

short_description: Manage Open CAS software

description:
  - Deploy Open CAS configuration

options:
  gather_facts:
    description:
      - gathers facts about Open CAS configuration on host
    required: False

  zap:
    description:
      - empties Open CAS device configuration file
    required: False

  stop:
    description:
      - stops all Open CAS devices
    suboptions:
      flush:
        description:
          - Should data from cache devices be flushed to primary storage
    required: False

  check_cache_config:
    description:
      - check if cache device configuration is valid
    required: False
    suboptions:
      cache_device:
        description:
          - Path to device to be used as a cache
      id:
        description:
          - id of cache to be created
      cache_mode:
        description:
          - Caching mode for cache
        choices: ['wt', 'wb', 'wa', 'pt', 'wo']
        default: wt
      cleaning_policy:
        description:
          - cleaning policy to be used by cache
        choices: ['alru', 'acp', 'nop']
        default: alru
      promotion_policy:
        description:
          - promotion policy to be used by cache
        choices: ['always', 'nhit']
        default: always
      line_size:
        description:
          - cache line size in kb
        choices: [4, 8, 16, 32, 64]
        default: 4
      io_class:
        description:
          - name of io classification file (located in /etc/opencas/)

  configure_cache_device:
    description:
      - configure and start cache device
    required: False
    suboptions:
      cache_device:
        description:
          - Path to device to be used as a cache
      id:
        description:
          - id of cache to be created
      cache_mode:
        description:
          - Caching mode for cache
        choices: ['wt', 'wb', 'wa', 'pt', 'wo']
        default: wt
      cleaning_policy:
        description:
          - cleaning policy to be used by cache
        choices: ['alru', 'acp', 'nop']
        default: alru
      promotion_policy:
        description:
          - promotion policy to be used by cache
        choices: ['always', 'nhit']
        default: always
      line_size:
        description:
          - cache line size in kb
        choices: [4, 8, 16, 32, 64]
        default: 4
      io_class:
        description:
          - name of io classification file (located in /etc/opencas/)

  check_core_config:
    description:
      - check if core configuration is valid
    required: False
    suboptions:
      id:
        description:
          - id of core device to be added
      cache_id:
        description:
          - id of cache device which will be servicing this core
      cached_volume:
        description:
          - path to device to be cached

  configure_core_device:
    description:
      - configure and add device to cache
    required: False
    suboptions:
      id:
        description:
          - id of core device to be added
      cache_id:
        description:
          - id of cache device which will be servicing this core
      cached_volume:
        description:
          - path to device to be cached
...
"""

EXAMPLES = """
- name: Gather facts about opencas installation
  cas:
    gather_facts: True

- name: Validate CAS cache configuration
  cas:
    check_cache_config:
      path: /dev/nvme0n1
      cache_id: 2
      mode: wb
      line_size: 8

- name: Configure and start CAS cache
  cas:
    configure_cache_device:
      path: /dev/nvme0n1
      cache_id: 2
      mode: wb
      line_size: 8

- name: Configure and add core device to CAS cache
  cas:
    configure_core_device:
      path: /dev/sda
      cache_id: 2
      core_id: 3

- name: Remove Open CAS devices configuration
  cas:
    zap: True

- name: Stop all Open CAS devices
  cas:
    stop:
      flush: True
"""

RETURN = """ # """


def gather_facts():
    ret = {}
    if cas_util is None:
        ret["opencas_installed"] = False
        return ret

    try:
        ret["opencas_installed_version"] = cas_util.get_cas_version()
        ret["opencas_installed"] = True
    except:
        ret["opencas_installed"] = False
        return ret

    try:
        config = cas_util.cas_config.from_file(
            cas_util.cas_config.default_location
        )
    except:
        ret["opencas_config_nonempty"] = False
    else:
        ret["opencas_config_nonempty"] = not config.is_empty()

    ret["opencas_devices_started"] = len(cas_util.get_caches_list()) != 0

    return ret


def zap():
    try:
        original_config = cas_util.cas_config.from_file(
            cas_util.cas_config.default_location
        )
    except:
        return False

    if original_config.is_empty():
        return False

    empty_config = cas_util.cas_config(version_tag=original_config.version_tag)

    empty_config.write(cas_util.cas_config.default_location)

    return True


def stop(flush):
    if len(cas_util.get_caches_list()) == 0:
        return False

    cas_util.stop(flush)

    if len(cas_util.get_caches_list()) != 0:
        raise Exception("Couldn't stop all cache devices")

    return True


def handle_core_config(config):
    try:
        path = config["cached_volume"]
        cache_id = int(config["cache_id"])
        core_id = int(config["id"])
    except:
        raise Exception("Missing core config parameters")

    return (path, core_id, cache_id)


def check_core_config(config):
    path, core_id, cache_id = handle_core_config(config)

    core_config = cas_util.cas_config.core_config(cache_id, core_id, path)

    core_config.validate_config()


def configure_core_device(config):
    path, core_id, cache_id = handle_core_config(config)

    try:
        config = cas_util.cas_config.from_file(
            cas_util.cas_config.default_location
        )
    except:
        raise

    config_copy = deepcopy(config)

    changed = True
    core_config = cas_util.cas_config.core_config(cache_id, core_id, path)

    try:
        config.insert_core(core_config)
    except cas_util.cas_config.AlreadyConfiguredException:
        changed = False
    else:
        config.write(cas_util.cas_config.default_location)

    if cas_util.is_core_added(core_config):
        return changed

    try:
        cas_util.add_core(core_config, False)
    except cas_util.casadm.CasadmError as e:
        config_copy.write(cas_util.cas_config.default_location)
        raise Exception("Internal casadm error({0})".format(e.result.stderr))
    except:
        config_copy.write(cas_util.cas_config.default_location)
        raise

    return True


def handle_cache_config(config):
    try:
        path = config["cache_device"]
        cache_id = int(config["id"])
        cache_mode = config["cache_mode"]
    except:
        raise Exception("Missing cache config parameters")

    params = dict()
    cache_line_size = config.get("line_size")
    if cache_line_size:
        params["cache_line_size"] = str(cache_line_size)

    io_class = config.get("io_class")
    if io_class:
        params["ioclass_file"] = "/etc/opencas/ansible/{0}".format(io_class)

    cleaning_policy = config.get("cleaning_policy")
    if cleaning_policy:
        params["cleaning_policy"] = cleaning_policy

    promotion_policy = config.get("promotion_policy")
    if promotion_policy:
        params["promotion_policy"] = promotion_policy

    force = config.get("force")

    return (path, cache_id, cache_mode, params, force)


def check_cache_config(config):
    path, cache_id, cache_mode, params, force = handle_cache_config(config)

    cache_config = cas_util.cas_config.cache_config(
        cache_id, path, cache_mode, **params
    )
    cache_config.validate_config(force)


def configure_cache_device(config):
    path, cache_id, cache_mode, params, force = handle_cache_config(config)

    try:
        config = cas_util.cas_config.from_file(
            cas_util.cas_config.default_location
        )
    except:
        raise

    config_copy = deepcopy(config)

    new_cache_config = cas_util.cas_config.cache_config(
        cache_id, path, cache_mode, **params
    )

    changed = True
    try:
        config.insert_cache(new_cache_config)
    except cas_util.cas_config.AlreadyConfiguredException:
        changed = False
    else:
        config.write(cas_util.cas_config.default_location)

    if cas_util.is_cache_started(new_cache_config):
        return changed

    try:
        cas_util.start_cache(new_cache_config, load=False, force=force)
        cas_util.configure_cache(new_cache_config)
    except cas_util.casadm.CasadmError as e:
        config_copy.write(cas_util.cas_config.default_location)
        raise Exception("Internal casadm error({0})".format(e.result.stderr))
    except:
        config_copy.write(cas_util.cas_config.default_location)
        raise

    return True


argument_spec = {
    "gather_facts": {"type": "bool", "required": False},
    "zap": {"type": "bool", "required": False},
    "stop": {"type": "dict", "required": False},
    "check_cache_config": {"type": "dict", "required": False},
    "configure_cache_device": {"type": "dict", "required": False},
    "check_core_config": {"type": "dict", "required": False},
    "configure_core_device": {"type": "dict", "required": False},
}


def setup_module_object():
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)

    return module


def run_task(module):
    ret = {"changed": False, "failed": False, "ansible_facts": {}}

    arg_gather_facts = module.params["gather_facts"]
    if arg_gather_facts:
        ret["ansible_facts"] = gather_facts()
        return ret

    arg_zap = module.params["zap"]
    if arg_zap:
        ret["changed"] = zap()
        return ret

    arg_stop = module.params["stop"]
    if arg_stop:
        ret["changed"] = ret["changed"] or stop(arg_stop["flush"])
        return ret

    arg_check_cache_config = module.params["check_cache_config"]
    if arg_check_cache_config:
        check_cache_config(arg_check_cache_config)
        return ret

    arg_check_core_config = module.params["check_core_config"]
    if arg_check_core_config:
        check_core_config(arg_check_core_config)
        return ret

    arg_configure_cache_device = module.params["configure_cache_device"]
    if arg_configure_cache_device:
        ret["changed"] = ret["changed"] or configure_cache_device(
            arg_configure_cache_device
        )
        return ret

    arg_configure_core_device = module.params["configure_core_device"]
    if arg_configure_core_device:
        ret["changed"] = ret["changed"] or configure_core_device(
            arg_configure_core_device
        )
        return ret

    return ret


def main():
    module = setup_module_object()

    try:
        ret = run_task(module)
    except Exception as e:
        module.fail_json(msg="{0}: {1}".format(type(e).__name__, str(e)))

    module.exit_json(**ret)


from ansible.module_utils.basic import AnsibleModule

if __name__ == "__main__":
    main()
