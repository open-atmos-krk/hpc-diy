from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import cluster_control.main as main


def test_add_static_dhcp_entry_writes_expected_line(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "get_dhcp_config_path", lambda: str(tmp_path / "static_dhcp.conf"))
    monkeypatch.setattr(main, "pop_available_ip", lambda: "172.16.100.10")
    monkeypatch.setattr(main, "_next_node_name", lambda: "jetson_0")

    main._add_static_dhcp_entry("aa:bb:cc:dd:ee:ff")

    content = (tmp_path / "static_dhcp.conf").read_text()
    assert "dhcp-host=aa:bb:cc:dd:ee:ff,jetson_0, 172.16.100.10\n" == content


def test_restart_dnsmasq_success(monkeypatch):
    run = Mock(return_value=SimpleNamespace(returncode=0, stderr=""))
    monkeypatch.setattr(main.subprocess, "run", run)

    main._restart_dnsmasq()

    run.assert_called_once()


def test_restart_dnsmasq_failure(monkeypatch, capsys):
    run = Mock(return_value=SimpleNamespace(returncode=1, stderr="boom"))
    monkeypatch.setattr(main.subprocess, "run", run)

    main._restart_dnsmasq()

    captured = capsys.readouterr()
    assert "Failed to restart dnsmasq" in captured.out


def test_register_node_success(monkeypatch):
    monkeypatch.setattr(main, "_add_static_dhcp_entry", Mock())
    monkeypatch.setattr(main, "_restart_dnsmasq", Mock())

    response = main.register_node(main.Node(mac_address="aa:bb:cc:dd:ee:ff"))

    assert response["status_code"] == 200
    assert response["mac"] == "aa:bb:cc:dd:ee:ff"


def test_register_node_failure(monkeypatch):

    def boom(_mac):
        raise RuntimeError("fail")

    monkeypatch.setattr(main, "_add_static_dhcp_entry", boom)
    monkeypatch.setattr(main, "_restart_dnsmasq", Mock())

    response = main.register_node(main.Node(mac_address="aa:bb:cc:dd:ee:ff"))

    assert response["status_code"] == 500


def test_next_node_name_when_empty(monkeypatch, tmp_path):
    dhcp_file = tmp_path / "static_dhcp.conf"
    dhcp_file.write_text("", encoding="utf-8")
    monkeypatch.setattr(main, "get_dhcp_config_path", lambda: str(dhcp_file))

    name = main._next_node_name()

    assert name == "jetson_0"


def test_next_node_name_increments(monkeypatch, tmp_path):
    dhcp_file = tmp_path / "static_dhcp.conf"
    dhcp_file.write_text("dhcp-host=aa:bb:cc,jetson_7, 192.168.0.2\n", encoding="utf-8")
    monkeypatch.setattr(main, "get_dhcp_config_path", lambda: str(dhcp_file))

    name = main._next_node_name()

    assert name == "jetson_8"


def test_next_node_name_invalid_name_raises(monkeypatch, tmp_path):
    dhcp_file = tmp_path / "static_dhcp.conf"
    dhcp_file.write_text("dhcp-host=aa:bb:cc,jetson, 192.168.0.2\n", encoding="utf-8")
    monkeypatch.setattr(main, "get_dhcp_config_path", lambda: str(dhcp_file))

    with pytest.raises(RuntimeError, match="Unexpected node name format"):
        main._next_node_name()


def test_next_node_name_missing_name_raises(monkeypatch, tmp_path):
    dhcp_file = tmp_path / "static_dhcp.conf"
    dhcp_file.write_text("dhcp-host=aa:bb:cc\n", encoding="utf-8")
    monkeypatch.setattr(main, "get_dhcp_config_path", lambda: str(dhcp_file))

    with pytest.raises(RuntimeError, match="Unexpected node name format"):
        main._next_node_name()
