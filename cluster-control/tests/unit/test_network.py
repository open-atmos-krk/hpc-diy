import ipaddress

import cluster_control.utils.network as network


def test_parse_interface_reads_value(tmp_path):
    conf = tmp_path / "dnsmasq.conf"
    conf.write_text("interface = enp0s9\n", encoding="utf-8")

    iface = network._parse_interface(conf)

    assert iface == "enp0s9"


def test_parse_interface_ignores_comments(tmp_path):
    conf = tmp_path / "dnsmasq.conf"
    conf.write_text("interface=enp0s8 # comment\n", encoding="utf-8")

    iface = network._parse_interface(conf)

    assert iface == "enp0s8"


def test_parse_interface_skips_unrelated_lines(tmp_path):
    conf = tmp_path / "dnsmasq.conf"
    conf.write_text("domain-needed\n", encoding="utf-8")

    iface = network._parse_interface(conf)

    assert iface == ""


def test_parse_dhcp_ranges(tmp_path):
    conf = tmp_path / "dnsmasq.conf"
    conf.write_text("dhcp-range=172.16.0.10,172.16.0.50,255.255.255.0,24h\n", encoding="utf-8")

    ranges = network._parse_dhcp_ranges(conf)

    assert ranges == [
        (ipaddress.IPv4Address("172.16.0.10"), ipaddress.IPv4Address("172.16.0.50"))
    ]


def test_collect_available_ips_excludes_ranges_and_iface():
    subnet = ipaddress.ip_network("172.16.0.0/29")
    dhcp_ranges = [
        (ipaddress.IPv4Address("172.16.0.2"), ipaddress.IPv4Address("172.16.0.3"))
    ]
    excludes = [ipaddress.IPv4Address("172.16.0.1")]

    available = network._collect_available_ips(subnet, dhcp_ranges, excludes)

    assert available == [
        ipaddress.IPv4Address("172.16.0.4"),
        ipaddress.IPv4Address("172.16.0.5"),
        ipaddress.IPv4Address("172.16.0.6"),
    ]


def test_get_available_ips_uses_dnsmasq_config(monkeypatch, tmp_path):
    conf = tmp_path / "dnsmasq.conf"
    static_conf = tmp_path / "static_dhcp.conf"
    conf.write_text(
        "interface=enp0s9\n"
        "dhcp-range=172.16.0.10,172.16.0.50,255.255.255.0,24h\n",
        encoding="utf-8",
    )
    static_conf.write_text("dhcp-host=aa:bb:cc,jetson_0, 172.16.0.20\n", encoding="utf-8")
    monkeypatch.setattr(network, "get_dnsmasq_config_path", lambda: str(conf))
    monkeypatch.setattr(network, "get_dhcp_config_path", lambda: str(static_conf))
    monkeypatch.setattr(network, "_get_iface_network", lambda _iface: ipaddress.ip_network("172.16.0.0/24"))
    monkeypatch.setattr(network, "_get_iface_ip", lambda _iface: ipaddress.IPv4Address("172.16.0.1"))

    available = network.get_available_ips()

    assert ipaddress.IPv4Address("172.16.0.1") not in available
    assert ipaddress.IPv4Address("172.16.0.10") not in available
    assert ipaddress.IPv4Address("172.16.0.20") not in available
