#
# Copyright(c) 2012-2019 Intel Corporation
# SPDX-License-Identifier: BSD-3-Clause-Clear
#

import pytest
from mock import patch, Mock
import helpers as h

import cas
import opencas


class AnsibleFailJson(Exception):
    pass


class AnsibleExitJson(Exception):
    pass


class MockAnsibleModule(object):
    def __init__(self, arg_spec):
        self.params = {}
        for key, value in arg_spec.items():
            if value["type"] == "bool":
                self.params[key] = False
            else:
                self.params[key] = {}

    def fail_json(*args, **kwargs):
        kwargs["failed"] = True
        raise AnsibleFailJson(kwargs)

    def exit_json(*args, **kwargs):
        if "changed" not in kwargs:
            kwargs["changed"] = False

        raise AnsibleExitJson(kwargs)


def setup_module_with_params(**params):
    mock_module = MockAnsibleModule(cas.argument_spec)
    for k, v in params.items():
        mock_module.params[k] = v

    return mock_module


@patch("opencas.get_cas_version")
@patch("cas.setup_module_object")
def test_module_get_facts_not_installed(mock_setup_module, mock_get_version):
    mock_get_version.side_effect = opencas.casadm.CasadmError("casadm error")
    mock_setup_module.return_value = setup_module_with_params(gather_facts=True)

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'opencas_installed': False")


@patch("opencas.get_cas_version")
@patch("opencas.get_caches_list")
@patch("cas.setup_module_object")
def test_module_get_facts_installed(
    mock_setup_module, mock_get_caches_list, mock_get_version
):
    mock_get_version.return_value = {
        "Open CAS Kernel Module": "03.08.00.01131011",
        "Open CAS Disk Kernel Module": "03.08.00.01131011",
        "Open CAS CLI Utility": "03.08.00.01131011",
    }
    mock_setup_module.return_value = setup_module_with_params(gather_facts=True)

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'opencas_installed': True")
    e.match("03.08.00.01131011")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_module_zap_no_file(mock_setup_module, mock_config_from_file):
    mock_setup_module.return_value = setup_module_with_params(zap=True)
    mock_config_from_file.side_effect = IOError()

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    mock_setup_module.assert_called_once()
    e.match("'changed': False")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_module_zap_config_empty(mock_setup_module, mock_config_from_file):
    mock_setup_module.return_value = setup_module_with_params(zap=True)
    mock_config_from_file.return_value = opencas.cas_config()

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': False")


mock_config_file = opencas.cas_config(
    version_tag="DEADBEEF",
    caches={"1": opencas.cas_config.cache_config(1, "/dev/dummy", "WT")},
    cores=[opencas.cas_config.core_config(1, 1, "/dev/dummycore")],
)


@patch("opencas.cas_config.from_file")
@patch("opencas.cas_config")
@patch("cas.setup_module_object")
def test_module_zap_config(
    mock_setup_module, mock_new_config, mock_config_from_file
):
    mock_setup_module.return_value = setup_module_with_params(zap=True)
    mock_config_from_file.return_value = mock_config_file
    new_config = Mock()
    mock_new_config.return_value = new_config

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    new_config.write.assert_called_once()
    mock_new_config.assert_called_with(version_tag="DEADBEEF")
    e.match("'changed': True")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_no_devices(mock_setup_module, mock_stop, mock_get_list):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": True}
    )
    mock_get_list.return_value = []

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    mock_stop.assert_not_called()
    e.match("'changed': False")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_list_exception(mock_setup_module, mock_stop, mock_get_list):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": True}
    )
    mock_get_list.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_stop.assert_not_called()
    e.match("'failed': True")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_exception(mock_setup_module, mock_stop, mock_get_list):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": True}
    )
    mock_get_list.return_value = [{}]
    mock_stop.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_stop.assert_called_with(True)
    e.match("'failed': True")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_no_devices_stopped(
    mock_setup_module, mock_stop, mock_get_list
):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": False}
    )

    # We're using empty dictionaries just to indicate devices count
    # Here no caches were stopped between mock calls
    mock_get_list.side_effect = [[{}, {}, {}], [{}, {}, {}]]

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_stop.assert_called_with(False)
    e.match("'failed': True")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_some_devices_stopped(
    mock_setup_module, mock_stop, mock_get_list
):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": False}
    )
    mock_get_list.side_effect = [[{}, {}, {}], [{}]]

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_stop.assert_called_with(False)
    e.match("'failed': True")


@patch("opencas.get_caches_list")
@patch("opencas.stop")
@patch("cas.setup_module_object")
def test_module_stop_all_devices_stopped(
    mock_setup_module, mock_stop, mock_get_list
):
    mock_setup_module.return_value = setup_module_with_params(
        stop={"flush": False}
    )
    mock_get_list.side_effect = [[{}, {}, {}], []]

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    mock_stop.assert_called_with(False)
    e.match("'changed': True")


@pytest.mark.parametrize(
    "cache_params",
    [
        {"id": "1"},
        {"cache_device": "/dev/dummy"},
        {"cache_mode": "WT"},
        {"id": "1", "cache_device": "/dev/dummy"},
        {"cache_device": "/dev/dummy", "cache_mode": "WT"},
        {"cache_device": "/dev/dummy", "cache_mode": "WT"},
        {
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
            "io_class": "dinosaurs.vbs",
        },
        {
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
            "cleaning_policy": "acp",
        },
        {"io_class": "best_config.rar"},
    ],
)
@patch("cas.setup_module_object")
def test_module_check_cache_device_missing_params(
    mock_setup_module, cache_params
):
    mock_setup_module.return_value = setup_module_with_params(
        check_cache_config=cache_params
    )

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    e.match("Missing")
    e.match("'failed': True")


@patch("opencas.cas_config.cache_config.validate_config")
@patch("cas.setup_module_object")
def test_module_check_cache_device_validate_failed(
    mock_setup_module, mock_validate
):
    mock_setup_module.return_value = setup_module_with_params(
        check_cache_config={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_validate.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_validate.assert_called()
    e.match("'failed': True")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_no_config(mock_setup_module, mock_from_file):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_from_file.side_effect = ValueError()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_from_file.assert_called()
    e.match("'failed': True")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_insert_failed(mock_setup_module, mock_from_file):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_core.side_effect = Exception()
    mock_from_file.return_value = mock_config

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_config.insert_cache.assert_called_once()
    e.match("'failed': True")


@patch("opencas.start_cache")
@patch("opencas.is_cache_started")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_already_configured_and_started(
    mock_setup_module, mock_from_file, mock_cache_started, mock_start_cache
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_cache.side_effect = (
        opencas.cas_config.AlreadyConfiguredException()
    )
    mock_from_file.return_value = mock_config
    mock_cache_started.return_value = True

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': False")
    mock_start_cache.assert_not_called()


@patch("opencas.is_cache_started")
@patch("opencas.start_cache")
@patch("opencas.configure_cache")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_not_configured_not_started(
    mock_setup_module,
    mock_from_file,
    mock_configure_cache,
    mock_start_cache,
    mock_cache_started,
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_from_file.return_value = mock_config
    mock_cache_started.return_value = False

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': True")

    mock_config.write.assert_called()

    mock_start_cache.assert_called_once()
    (args, kwargs) = mock_start_cache.call_args
    cache_arg = args[0]
    assert kwargs["load"] == False
    assert kwargs["force"] == None
    assert type(cache_arg) == opencas.cas_config.cache_config
    assert cache_arg.cache_id == 1
    assert cache_arg.device == "/dev/dummy"
    assert cache_arg.cache_mode == "WT"

    mock_configure_cache.assert_called_once()
    (args, kwargs) = mock_configure_cache.call_args
    assert args[0] == cache_arg


@patch("opencas.is_cache_started")
@patch("opencas.start_cache")
@patch("opencas.configure_cache")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_configured_not_started(
    mock_setup_module,
    mock_from_file,
    mock_configure_cache,
    mock_start_cache,
    mock_cache_started,
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_cache.side_effect = (
        opencas.cas_config.AlreadyConfiguredException()
    )
    mock_from_file.return_value = mock_config
    mock_cache_started.return_value = False

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': True")

    mock_config.write.assert_not_called()

    mock_start_cache.assert_called_once()
    (args, kwargs) = mock_start_cache.call_args
    cache_arg = args[0]
    assert kwargs["load"] == False
    assert kwargs["force"] == None
    assert type(cache_arg) == opencas.cas_config.cache_config
    assert cache_arg.cache_id == 1
    assert cache_arg.device == "/dev/dummy"
    assert cache_arg.cache_mode == "WT"

    mock_configure_cache.assert_called_once()
    (args, kwargs) = mock_configure_cache.call_args
    assert args[0] == cache_arg


@patch("opencas.is_cache_started")
@patch("opencas.start_cache")
@patch("opencas.configure_cache")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_cache_not_configured_not_started_start_failed(
    mock_setup_module,
    mock_from_file,
    mock_configure_cache,
    mock_start_cache,
    mock_cache_started,
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_cache_device={
            "id": "1",
            "cache_device": "/dev/dummy",
            "cache_mode": "WT",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_from_file.return_value = mock_config
    mock_cache_started.return_value = False
    mock_start_cache.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_config.write.assert_called()

    mock_start_cache.assert_called_once()

    e.match("'failed': True")
    mock_configure_cache.assert_not_called()
    assert len(mock_config.copies) == 1
    mock_config.copies[0].write.assert_called_once()


@pytest.mark.parametrize(
    "core_params",
    [
        {"cache_id": "1"},
        {"id": "1"},
        {"cached_volume": "/dev/dummy"},
        {"id": "1", "cached_volume": "/dev/dummy"},
        {"cache_id": "1", "cached_volume": "/dev/dummy"},
        {"id": "one", "cache_id": "1", "cached_volume": "/dev/dummy"},
    ],
)
@patch("cas.setup_module_object")
def test_module_check_core_device_missing_params(mock_setup_module, core_params):
    mock_setup_module.return_value = setup_module_with_params(
        check_core_config=core_params
    )

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    e.match("Missing")
    e.match("'failed': True")


@patch("opencas.cas_config.core_config.validate_config")
@patch("cas.setup_module_object")
def test_module_check_cache_device_validate_failed(
    mock_setup_module, mock_validate
):
    mock_setup_module.return_value = setup_module_with_params(
        check_core_config={
            "id": "1",
            "cache_id": "1",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_validate.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_validate.assert_called()
    e.match("'failed': True")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_no_config(mock_setup_module, mock_from_file):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "1",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_from_file.side_effect = ValueError()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_from_file.assert_called()
    e.match("'failed': True")


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_insert_failed(mock_setup_module, mock_from_file):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "1",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_core.side_effect = Exception()
    mock_from_file.return_value = mock_config

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_config.insert_core.assert_called_once()
    e.match("'failed': True")


@patch("opencas.add_core")
@patch("opencas.is_core_added")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_already_added(
    mock_setup_module, mock_from_file, mock_core_added, mock_add_core
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "1",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_core.side_effect = (
        opencas.cas_config.AlreadyConfiguredException()
    )
    mock_from_file.return_value = mock_config
    mock_core_added.return_value = True

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': False")
    mock_add_core.assert_not_called()


@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_insert_failed(mock_setup_module, mock_from_file):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "1",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_core.side_effect = Exception()
    mock_from_file.return_value = mock_config

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_config.insert_core.assert_called_once()
    e.match("'failed': True")


@patch("opencas.is_core_added")
@patch("opencas.add_core")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_not_configured_not_added(
    mock_setup_module, mock_from_file, mock_add_core, mock_core_added
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "2",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_from_file.return_value = mock_config
    mock_core_added.return_value = False

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': True")

    mock_config.write.assert_called()

    mock_add_core.assert_called_once()
    (args, kwargs) = mock_add_core.call_args
    core_arg = args[0]
    assert type(core_arg) == opencas.cas_config.core_config
    assert core_arg.cache_id == 2
    assert core_arg.core_id == 1
    assert core_arg.device == "/dev/dummy"


@patch("opencas.is_core_added")
@patch("opencas.add_core")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_configured_not_added(
    mock_setup_module, mock_from_file, mock_add_core, mock_core_added
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "2",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_config.insert_core.side_effect = (
        opencas.cas_config.AlreadyConfiguredException()
    )
    mock_from_file.return_value = mock_config
    mock_core_added.return_value = False

    with pytest.raises(AnsibleExitJson) as e:
        cas.main()

    e.match("'changed': True")

    mock_config.write.assert_not_called()

    mock_add_core.assert_called_once()
    (args, kwargs) = mock_add_core.call_args
    core_arg = args[0]
    assert type(core_arg) == opencas.cas_config.core_config
    assert core_arg.cache_id == 2
    assert core_arg.core_id == 1
    assert core_arg.device == "/dev/dummy"


@patch("opencas.is_core_added")
@patch("opencas.add_core")
@patch("opencas.cas_config.from_file")
@patch("cas.setup_module_object")
def test_modlue_configure_core_not_configured_not_added_add_failed(
    mock_setup_module, mock_from_file, mock_add_core, mock_core_added
):
    mock_setup_module.return_value = setup_module_with_params(
        configure_core_device={
            "id": "1",
            "cache_id": "2",
            "cached_volume": "/dev/dummy",
        }
    )
    mock_config = h.CopyableMock()
    mock_config.mock_add_spec(opencas.cas_config)
    mock_from_file.return_value = mock_config
    mock_core_added.return_value = False
    mock_add_core.side_effect = Exception()

    with pytest.raises(AnsibleFailJson) as e:
        cas.main()

    mock_config.write.assert_called()

    mock_add_core.assert_called_once()
    e.match("'failed': True")

    assert len(mock_config.copies) == 1
    mock_config.copies[0].write.assert_called_once()
