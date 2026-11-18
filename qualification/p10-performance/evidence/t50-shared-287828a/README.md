# Shared frozen T50 inputs for the 287828a release and candidates

The isolated materializer at `0f5942a71592bf472c0bf18eee6ae7dfd79fa338`
matched the product tree outside documentation and the target adapter at
`287828aac07ffad2252785b73a52a59fc07b3409`. The generator tree matched the
previous qualified `12f2151` materializer. The frozen receipt and performance
target digests remained unchanged.

This one shared stage contains 50 distinct 6000×4000 RGB16 focus TIFFs,
one independent sharp RGB16 TIFF and one categorical depth TIFF. All 52 file
digests, codec-decoded digests and independent zlib-decoded digests match the
frozen manifest. Verified retained bytes were 2,775,174,405. Input ordering is
`focus_000.tif` through `focus_049.tif`. Truth files stay separate from application
inputs. The exact materialization receipt SHA-256 is
`62200bca0567ae06e2b6d3eba406aea259e601904c756b64ea7b245ede2625a4`.

The generator ran on logical CPU 2 with nice +12, idle I/O and numerical
thread limits of one. It completed in 248.611 seconds and peaked at
83,436 KiB RSS. Disk availability at start and finish was 124,568,600,576 B
and 117,977,395,200 B, respectively. Host available memory was 42,380,328 KiB
and 43,708,112 KiB. The generator retained the original 15 GiB disk reserve
and recorded zero full-frame buffers. This stage ran zero benchmark jobs.

The live [stage receipt](shared-stage.json) identifies the read-only input
root and ownership-linked manifest. Each borrower verifies the same manifest
and returns the timing lease independently. Authenticated input cleanup is
the stage owner's responsibility after all borrowers release. [All frozen
records](materialization.json.gz) · [Commands and resource observations](raw-stage.tar.gz)
