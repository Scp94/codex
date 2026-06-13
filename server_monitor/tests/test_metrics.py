from monitor_platform.metrics import parse_meminfo, parse_net_dev


def test_parse_meminfo_uses_bytes():
    parsed = parse_meminfo(
        """MemTotal:       1024 kB
MemAvailable:    256 kB
SwapTotal:       128 kB
"""
    )

    assert parsed["MemTotal"] == 1024 * 1024
    assert parsed["MemAvailable"] == 256 * 1024
    assert parsed["SwapTotal"] == 128 * 1024


def test_parse_net_dev_extracts_receive_and_transmit_totals():
    parsed = parse_net_dev(
        """Inter-|   Receive                                                |  Transmit
 face |bytes    packets errs drop fifo frame compressed multicast|bytes    packets errs drop fifo colls carrier compressed
 eth0: 12345 10 1 0 0 0 0 0 98765 20 2 0 0 0 0 0
"""
    )

    assert parsed == [
        {
            "interface": "eth0",
            "rx_bytes": 12345,
            "rx_packets": 10,
            "rx_errors": 1,
            "tx_bytes": 98765,
            "tx_packets": 20,
            "tx_errors": 2,
        }
    ]

