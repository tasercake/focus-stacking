"""Exercise the same portable cases against a compiled, non-Python process."""
import subprocess


def test_compiled_target_uses_descriptor_without_reference_adapter(tmp_path):
    from pancake_conformance.cases.cli import cli_cases
    from pancake_conformance.runner import run_cases
    from pancake_conformance.target import TargetSpec

    source = tmp_path / "target.c"
    source.write_text(r'''
#include <stdio.h>
#include <string.h>
int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "--help") == 0) {
        puts("--sources --dest --fusion"); return 0;
    }
    for (int i = 1; i + 1 < argc; ++i) {
        if (strcmp(argv[i], "--fusion") == 0) {
            fprintf(stderr, "invalid fusion method: %s\n", argv[i+1]); return 2;
        }
    }
    fputs("missing sources or destination\n", stderr); return 2;
}
''')
    executable = tmp_path / "target"
    subprocess.run(["cc", str(source), "-o", str(executable)], check=True,
                   capture_output=True, text=True, timeout=30)
    descriptor = tmp_path / "target.toml"
    descriptor.write_text('schema_version=1\nname="compiled-example"\nroot="."\ncli=["./target"]\n'
                          '[stack]\ninput=["--sources","{inputs}"]\noutput=["--dest","{output}"]\n'
                          '[stack.options]\nmethod="--fusion"\n')
    target = TargetSpec.load(descriptor)
    cases = [case for case in cli_cases() if case.id in {"cli.help", "cli.reject.no-arguments", "cli.reject.method"}]
    results = run_cases(cases, target=target, output=tmp_path / "results")
    assert len(results) == 3
    assert all(result.status == "passed" for result in results), [r.error for r in results]
