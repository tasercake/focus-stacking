//! Same-handle cursor and row-band contracts for real TIFF decoding.

use std::cell::Cell;
use std::error::Error;
use std::fs::File;
use std::io::{self, Read, Seek, SeekFrom};

use super::{
    FileSource, Layout, MAX_TIFF_WORKERS, PARALLEL_MIN_PIXELS, lane_count, read_parallel,
    tile_spans,
};
use crate::image_io::profile_from_tiff;

/// Existing independent deflated RGB16 fixture with five partial-edged tile rows.
const TILED_RGB16: &[u8] = include_bytes!("../../../tests/data/tiled-rgb16-zip.tif");

/// Test failures include both source decoding errors and contract mismatches.
type TestResult = Result<(), Box<dyn Error>>;

/// Return a structured test failure without unwinding worker scopes.
///
/// # Errors
///
/// Reports a false condition with its contract name.
fn require(condition: bool, diagnostic: &str) -> TestResult {
    if condition {
        Ok(())
    } else {
        Err(io::Error::other(diagnostic.to_owned()).into())
    }
}

/// File positions and compressed bounds remain independent after interleaved seeks and reads.
///
/// # Errors
///
/// Reports source I/O or a cursor returning bytes from another tile.
#[test]
fn shared_cursors_keep_independent_positions_and_read_bounds() -> TestResult {
    let tmp = tempfile::NamedTempFile::new()?;
    std::fs::write(tmp.path(), b"abcdEFGH1234")?;
    let handle = File::open(tmp.path())?;
    let source = FileSource::new(&handle)?;
    let left_span = Cell::new(Some((2, 5)));
    let right_span = Cell::new(Some((7, 11)));
    let mut left = source.cursor(&left_span);
    let mut right = source.cursor(&right_span);
    let _ = left.seek(SeekFrom::Start(2))?;
    let mut bytes = [0_u8; 2];
    left.read_exact(&mut bytes)?;
    require(&bytes == b"cd", "left cursor began at the wrong tile")?;
    let _ = right.seek(SeekFrom::End(-5))?;
    right.read_exact(&mut bytes)?;
    require(&bytes == b"H1", "right cursor began at the wrong tile")?;
    let mut left_tail = Vec::new();
    let _ = left.read_to_end(&mut left_tail)?;
    require(left_tail == b"E", "left cursor escaped its compressed span")?;
    let mut right_tail = Vec::new();
    let _ = right.read_to_end(&mut right_tail)?;
    require(
        right_tail == b"23",
        "right cursor escaped its compressed span",
    )
}

/// Host CPUs, useful tile rows and the process cap all bound the number of lanes.
///
/// # Errors
///
/// Reports unexpected parallelism or excessive lanes.
#[test]
fn lanes_respect_low_affinity_small_images_and_row_count() -> TestResult {
    for (pixels, rows, cpus, expected) in [
        (PARALLEL_MIN_PIXELS, 16, 1, 1),
        (PARALLEL_MIN_PIXELS, 16, 2, 2),
        (PARALLEL_MIN_PIXELS, 16, 128, MAX_TIFF_WORKERS),
        (PARALLEL_MIN_PIXELS, 2, 128, 2),
        (PARALLEL_MIN_PIXELS, 1, 128, 1),
        (10_000, 16, 128, 1),
    ] {
        require(
            lane_count(pixels, rows, cpus) == expected,
            "TIFF lane allocation exceeded its useful resource bounds",
        )?;
    }
    Ok(())
}

/// Three actual decode lanes preserve the edge rows and propagate a later corrupt tile.
///
/// # Errors
///
/// Reports fixture setup, malformed data acceptance or a wrong normalized RGB code.
#[test]
fn row_workers_match_every_sample_and_report_later_tile_failure() -> TestResult {
    let tmp = tempfile::NamedTempFile::new()?;
    for corrupt in [false, true] {
        let mut content = TILED_RGB16.to_vec();
        if corrupt {
            // First IFD count array starts at 364. Its last LONG belongs to tile 24.
            content
                .get_mut(460..464)
                .ok_or_else(|| io::Error::other("fixture is missing its last tile count"))?
                .copy_from_slice(&1_u32.to_le_bytes());
        }
        std::fs::write(tmp.path(), content)?;
        let handle = File::open(tmp.path())?;
        let source = FileSource::new(&handle)?;
        let cap = Cell::new(None);
        let mut decoder = source.decoder(&cap)?;
        let layout = Layout::read(&mut decoder)?
            .ok_or_else(|| io::Error::other("fixture is ineligible for tiled decoding"))?;
        let spans = tile_spans(&mut decoder, &layout, source.length)?;
        let mut working = vec![0.0_f32; 199_689];
        let completed = read_parallel(&source, &layout, &spans, &mut working, 3);
        if corrupt {
            let diagnostic = completed
                .err()
                .ok_or_else(|| io::Error::other("a later lane accepted a short compressed tile"))?;
            require(diagnostic.contains("TIFF tile 24"), &diagnostic)?;
        } else {
            require(completed?, "three available lanes were not used")?;
            require(
                profile_from_tiff(decoder).as_deref()
                    == Some(include_bytes!("../../../tests/data/srgb.png.icc").as_slice()),
                "the original decoder lost the ICC profile after adjacent band reads",
            )?;
            for (index, value) in working.into_iter().enumerate() {
                let code = u16::try_from(index % 65_536)?;
                require(
                    value.to_bits() == (f32::from(code) / 65_535.0).to_bits(),
                    "row-band output changed an encoded RGB16 sample",
                )?;
            }
        }
    }
    Ok(())
}
