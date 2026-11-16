def test_sprint_starts_with_native_alternate_input_workflows():
    from pancake_conformance.cases.coverage_sprint import sprint_cases
    cases = sprint_cases()
    assert {c.id for c in cases} >= {
        "interface.sprint.viewer-input", "interface.sprint.frame-context",
        "interface.sprint.viewport-export"}
    assert len({c.id for c in cases}) == len(cases)
    assert "algorithms.sprint.black-translation" in {c.id for c in cases}
    assert len([c for c in cases if c.id.startswith("algorithms.sprint.native-input.")]) == 9
