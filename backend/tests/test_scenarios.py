from incident_lab.runtime import store


def test_scenario_activation_and_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RUNTIME_DIRECTORY", tmp_path)
    monkeypatch.setattr(store, "SCENARIO_PATH", tmp_path / "scenario.json")
    monkeypatch.setattr(store, "DEPLOYMENTS_PATH", tmp_path / "deployments.json")
    active = store.activate_scenario("payment_latency")
    assert active["payment_latency_ms"] == 1800
    assert store.load_scenario()["name"] == "payment_latency"
    reset = store.activate_scenario("baseline")
    assert reset["payment_failure_rate"] == 0

