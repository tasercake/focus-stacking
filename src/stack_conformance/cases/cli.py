"""Public command-line contract. No imports from an application implementation."""
import hashlib
import re

from stack_conformance.model import Case
from stack_conformance.validators import assert_pixels_close, validate_image


def _help(ctx):
    result = ctx.command(["--help"])
    assert result.returncode == 0, result.stderr
    mapping = ctx.target.stack.get("options", {})
    terms = [token for token in (*ctx.target.stack.get("input", []), *ctx.target.stack.get("output", [])) if not token.startswith("{")]
    terms.extend(rule for rule in mapping.values() if isinstance(rule, str))
    for term in terms:
        assert term in result.stdout, f"missing documented CLI option {term}"


def _invalid_args(arguments):
    def run(ctx):
        result = ctx.command(arguments)
        assert result.returncode != 0, (result.returncode, result.stderr)
        assert result.stderr.strip(), "failed CLI must explain its error"
    return run


def _invalid_option(option, value):
    def run(ctx):
        fixture = ctx.fixture("odd")
        arguments = ctx.target.stack_arguments(fixture.paths, ctx.directory / "invalid.png", {option: value})
        result = ctx.command(arguments)
        assert result.returncode != 0, "invalid option unexpectedly accepted"
        diagnostic = result.stderr + result.stdout
        assert str(value) in diagnostic, f"error did not identify offending value {value}: {diagnostic}"
    return run


def _missing_required(kind):
    def run(ctx):
        fixture = ctx.fixture("odd")
        if kind == "input":
            arguments = [str(ctx.directory / "unused.png") if token == "{output}" else token
                         for token in ctx.target.stack.get("output", ["--output", "{output}"])]
        else:
            arguments = []
            for token in ctx.target.stack.get("input", ["--input", "{inputs}"]):
                arguments.extend(map(str, fixture.paths)) if token == "{inputs}" else arguments.append(token)
        result = ctx.command(arguments)
        assert result.returncode != 0 and result.stderr.strip()
    return run


def _device_conflict(ctx):
    fixture = ctx.fixture("odd")
    args = ctx.target.stack_arguments(fixture.paths, ctx.directory / "invalid.png", {"device": "cpu"})
    args.extend(ctx.target.stack["options"]["device"]["gpu"])
    result = ctx.command(args)
    assert result.returncode != 0 and result.stderr.strip(), "conflicting devices unexpectedly accepted"


def _unknown_option(ctx):
    fixture = ctx.fixture("odd")
    args = ctx.target.stack_arguments(fixture.paths, ctx.directory / "invalid.png", {})
    result = ctx.command([*args, "--conformance-deliberately-unknown-option"])
    assert result.returncode != 0
    assert "--conformance-deliberately-unknown-option" in result.stderr


def _bad_stack(options, paths=None):
    def run(ctx):
        fixture = ctx.fixture("odd")
        inputs = fixture.paths if paths is None else paths(ctx, fixture)
        result = ctx.stack(inputs, **options)
        assert result.returncode != 0, "invalid stack unexpectedly succeeded"
        assert result.stderr.strip(), "invalid stack produced no diagnostic"
        assert not result.output.exists(), "invalid stack published output"
    return run


def _order_and_dedup(ctx):
    fixture = ctx.fixture("focus")
    first = ctx.stack(fixture, method="hybrid")
    second = ctx.stack([*reversed(fixture.paths), fixture.paths[0]], method="hybrid")
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    assert_pixels_close(first.output, second.output, mean_limit=0, max_limit=0)


def _glob(ctx):
    fixture = ctx.fixture("odd")
    first = ctx.stack(fixture, method="hybrid")
    second = ctx.stack([fixture.paths[0].parent / "*.png"], method="hybrid")
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    assert_pixels_close(first.output, second.output, mean_limit=0, max_limit=0)


def _source_immutability(ctx):
    fixture = ctx.fixture("precision16")
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.paths}
    result = ctx.stack(fixture, method="hybrid", bit_depth=16, output_format="tif")
    assert result.returncode == 0, result.stderr
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.paths}


def _progress(ctx):
    result = ctx.stack(ctx.fixture("focus"), method="hybrid", quality_report=True)
    assert result.returncode == 0, result.stderr
    assert "sharpness" in result.stdout.lower()
    progress = [(int(a), int(b)) for a, b in re.findall(r"\[(\d+)/(\d+)\]", result.stderr)]
    assert progress, "no machine-observable CLI progress"
    assert progress[-1][0] == progress[-1][1]
    assert all(0 <= a <= b for a, b in progress)
    assert all(a <= b for a, b in zip([x[0] for x in progress], [x[0] for x in progress][1:], strict=False))


def _jpeg_precision_warning(ctx):
    result = ctx.stack(ctx.fixture("precision16"), method="hybrid", bit_depth=16, output_format="jpg")
    assert result.returncode == 0, result.stderr
    assert "16-bit" in result.stderr and "8-bit" in result.stderr
    validate_image(result.output, dtype="uint8")


def _output_failure(ctx):
    fixture = ctx.fixture("odd")
    output = ctx.directory / "missing-parent" / "output.png"
    args = ctx.target.stack_arguments(fixture.paths, output, {"device": "cpu", "pyramid_levels": 3})
    result = ctx.command(args)
    assert result.returncode != 0, "output to nonexistent parent unexpectedly succeeded"
    assert not output.exists()
    assert result.stderr.strip()


def _corrupt_inputs(ctx):
    paths = [ctx.directory / "broken1.png", ctx.directory / "broken2.png"]
    for path in paths:
        path.write_bytes(b"this is not an image")
    result = ctx.stack(paths)
    assert result.returncode != 0, "corrupt inputs unexpectedly succeeded"
    assert not result.output.exists()


def _overwrite_output(ctx):
    fixture = ctx.fixture("odd")
    output = ctx.directory / "existing.png"
    output.write_bytes(b"old result sentinel")
    result = ctx.command(ctx.target.stack_arguments(fixture.paths, output, {"device": "cpu", "method": "hybrid"}))
    assert result.returncode == 0, result.stderr
    validate_image(output, shape=fixture.shape, dtype="uint8", min_range=30)
    ctx.record_output(output)


def _failed_export_retention(ctx):
    fixture = ctx.fixture("odd")
    output = ctx.directory / "existing.unsupported-conformance-format"
    output.write_bytes(b"old result sentinel")
    result = ctx.command(ctx.target.stack_arguments(fixture.paths, output, {"device": "cpu"}))
    assert result.returncode != 0, "unsupported export unexpectedly succeeded"
    assert output.read_bytes() == b"old result sentinel", "failed export damaged existing file"


def cli_cases():
    cases = [Case("cli.help", "cli", _help, "Help describes public CLI surface")]
    invalid = {
        "no-arguments": [],
    }
    cases.extend(Case(f"cli.reject.{name}", "cli", _invalid_args(args), "Invalid arguments fail with diagnostic")
                 for name, args in invalid.items())
    for name, option, value in (("method", "method", "__invalid_method__"),
                                ("alignment", "alignment_mode", "__invalid_alignment__"),
                                ("reference", "alignment_reference", "__invalid_reference__"),
                                ("bit-depth", "bit_depth", 12), ("integer", "kernel_size", "__invalid_integer__")):
        cases.append(Case(f"cli.reject.{name}", "cli", _invalid_option(option, value)))
    cases.extend([Case("cli.reject.missing-input", "cli", _missing_required("input")),
                  Case("cli.reject.missing-output", "cli", _missing_required("output")),
                  Case("cli.reject.unknown-option", "cli", _unknown_option),
                  Case("cli.reject.device-conflict", "cli", _device_conflict)])
    for name, options in {
        "scale-zero": {"max_scale_step": 0}, "scale-one": {"max_scale_step": 1},
        "scale-negative": {"max_scale_step": -0.1}, "slab-one": {"slab_size": 1},
        "slab-negative": {"slab_size": -1}, "overlap-negative": {"slab_size": 2, "slab_overlap": -1},
        "overlap-too-large": {"slab_size": 2, "slab_overlap": 2},
    }.items():
        cases.append(Case(f"cli.reject.{name}", "cli", _bad_stack(options), "Invalid stack settings fail without output"))
    cases.extend([
        Case("cli.reject.no-files", "cli", _bad_stack({}, lambda c, f: [c.directory / "absent-*.png"])),
        Case("cli.reject.one-file", "cli", _bad_stack({}, lambda c, f: f.paths[:1])),
        Case("cli.reject.duplicate-single", "cli", _bad_stack({}, lambda c, f: [f.paths[0]] * 3)),
        Case("cli.reject.corrupt-images", "cli", _corrupt_inputs),
        Case("cli.reject.output-parent", "cli", _output_failure),
        Case("cli.paths.sorted-and-deduplicated", "cli", _order_and_dedup),
        Case("cli.paths.glob", "cli", _glob),
        Case("cli.inputs.unchanged", "cli", _source_immutability),
        Case("cli.progress-and-quality", "cli", _progress),
        Case("cli.export.jpeg-16bit-warning", "cli", _jpeg_precision_warning),
        Case("cli.export.overwrite", "cli", _overwrite_output),
        Case("cli.export.failed-retention", "cli", _failed_export_retention),
    ])
    return cases
