# Image I/O regressions

The image I/O production files at `bbb4767` match the retained coverage source
at `3dc9bcf`. The Rust 1.100.0 focused campaign exercised file-based profile
retention, malformed PNG/TIFF/DNG data, Bayer orientation, RGB and grayscale
precision, numeric frame limits, and the publication boundary after source or
staging changes. All fixtures were generated from the tests or checked into the
workspace.

The first regression exposed missing TIFF ICC bytes on import after exporting
a profiled RGB frame. PNG and JPEG passed. The direct TIFF directory reader
returned the exact 588-byte input profile from the emitted TIFF file. Calling
`image::ImageReader::into_decoder().icc_profile()` on that TIFF returned
`None` before any orientation call. The first application failure is retained
with the unchanged image implementation at `bbb4767`.
[Red test output](tiff-icc-red.log)

The application now recovers valid profile bytes from the original TIFF stream
through the pinned TIFF decoder's bounded directory API when the image decoder
has no profile. RGB8 and RGB16 export and import preserve the exact metadata,
samples and dimensions. The raster decode still owns native orientation and
color precision. The metadata fallback follows the existing handling of
missing or invalid optional profile tags.
