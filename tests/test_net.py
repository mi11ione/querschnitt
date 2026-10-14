"""RFC 9309 matching and the export-only rule."""
import pytest

from querschnitt import net


def test_longest_match_wins():
    rules = net.parse("User-agent: *\nAllow: /\nDisallow: /v1/\nAllow: /v1/public$\n")
    assert net.decide(rules, "/exports/index.json")
    assert not net.decide(rules, "/v1/affairs")
    assert net.decide(rules, "/v1/public") and not net.decide(rules, "/v1/public/x")


def test_agent_group_and_wildcards():
    txt = "User-agent: querschnitt\nDisallow: /*.gz$\n\nUser-agent: *\nDisallow: /\n"
    rules = net.parse(txt, net.UA)
    assert not net.decide(rules, "/exports/affairs.ndjson.gz") and net.decide(rules, "/exports/index.json")
    assert not net.decide(net.parse(txt, "other/1.0"), "/exports/index.json")


def test_only_published_exports():
    with pytest.raises(net.Refused):
        net.check("https://api.openparldata.ch/v1/affairs")
    with pytest.raises(net.Refused):
        net.check("https://example.org/exports/x")


def test_fail_closed(monkeypatch):
    net._ROBOTS.clear()
    monkeypatch.setitem(net._ROBOTS, "https://files.openparldata.ch", None)
    with pytest.raises(net.Refused):
        net.check(net.EXPORTS + "index.json")
    net._ROBOTS.clear()
