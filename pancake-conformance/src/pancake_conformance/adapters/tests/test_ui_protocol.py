def test_ui_identifier_contract_is_unique():
    from pancake_conformance.adapters.chimpstackr_ui import IDENTIFIER_CONTRACT

    assert len(IDENTIFIER_CONTRACT) == len(set(IDENTIFIER_CONTRACT))
    assert {"main.window", "stack.start", "export.start", "viewer", "alignment", "method.hybrid"} <= set(IDENTIFIER_CONTRACT)

