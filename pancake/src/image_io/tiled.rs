//! Typed streaming import of tiled DEFLATE RGB16 TIFFs.

use std::cell::Cell;
use std::fs::File;
use std::io::{self, BufReader, Read, Seek, SeekFrom};

use tiff::decoder::{ChunkType, Decoder, DecodingResult, DecodingSampleType};
use tiff::tags::Tag;

use super::{RgbImage, SampleEncoding, checked_pixel_count, profile_from_tiff};

/// Keep a reusable decoded tile to six MiB, with larger tiles using native raster import.
const MAX_TILE_PIXELS: usize = 1_048_576;

/// Bounds TIFF decompression reads to the current declared compressed tile.
#[derive(Debug)]
struct TileInput<'a> {
    /// Original source handle, retained across metadata, tile and ICC reads.
    input: &'a mut BufReader<File>,
    /// Logical stream position, including bytes delivered from the read buffer.
    position: u64,
    /// Tile start and exclusive end, or no cap during directory reads.
    span: &'a Cell<Option<(u64, u64)>>,
}

impl Read for TileInput<'_> {
    fn read(&mut self, buffer: &mut [u8]) -> io::Result<usize> {
        let bound = if let Some((start, end)) = self.span.get() {
            if self.position < start || self.position > end {
                return Err(io::Error::other("read outside the compressed TIFF tile"));
            }
            let remaining = end.saturating_sub(self.position);
            usize::try_from(remaining)
                .unwrap_or(usize::MAX)
                .min(buffer.len())
        } else {
            buffer.len()
        };
        let count = self.input.read(
            buffer
                .get_mut(..bound)
                .ok_or_else(|| io::Error::other("invalid TIFF read size"))?,
        )?;
        self.position = self
            .position
            .checked_add(u64::try_from(count).map_err(io::Error::other)?)
            .ok_or_else(|| io::Error::other("TIFF stream position overflowed"))?;
        Ok(count)
    }
}

impl Seek for TileInput<'_> {
    fn seek(&mut self, position: SeekFrom) -> io::Result<u64> {
        self.position = self.input.seek(position)?;
        Ok(self.position)
    }
}

/// Unoriented unsigned contiguous sample layout eligible for bounded typed decoding.
fn supports_streaming(decoder: &mut Decoder<TileInput<'_>>) -> bool {
    decoder.get_chunk_type() == ChunkType::Tile
        && matches!(decoder.colortype(), Ok(tiff::ColorType::RGB(16)))
        && matches!(decoder.find_tag_unsigned::<u16>(Tag::SamplesPerPixel), Ok(Some(3)))
        // TIFF tag values for Deflate and OldDeflate as recognized by the native decoder.
        && matches!(decoder.find_tag_unsigned::<u16>(Tag::Compression), Ok(Some(8 | 32_946)))
        && matches!(decoder.find_tag_unsigned::<u16>(Tag::Orientation), Ok(None | Some(1)))
        && decoder.image_buffer_layout().is_ok_and(|layout| {
            layout.planes == 1 && layout.sample_type == Some(DecodingSampleType::U16)
        })
}

/// Tile and output geometry kept in elements unless passed to the TIFF stride API.
#[derive(Debug)]
struct Layout {
    /// Pixels across the full raster.
    width: usize,
    /// Pixels down the full raster.
    height: usize,
    /// Pixels across a full encoded tile before edge padding is removed.
    tile_width: usize,
    /// Rows in a full tile before edge padding is removed.
    tile_height: usize,
    /// Number of tile columns, including the right edge.
    columns: usize,
}

impl Layout {
    /// Read exact tile dimensions and verify the optimized scratch limit.
    ///
    /// # Errors
    ///
    /// Rejects invalid dimensions or an unaddressable raster.
    fn read(decoder: &mut Decoder<TileInput<'_>>) -> Result<Option<Self>, String> {
        let (width, height) = decoder.dimensions().map_err(|error| error.to_string())?;
        let width = usize::try_from(width).map_err(|error| error.to_string())?;
        let height = usize::try_from(height).map_err(|error| error.to_string())?;
        let _pixels = checked_pixel_count(width, height)?;
        let tile_width = decoder
            .get_tag_unsigned::<usize>(Tag::TileWidth)
            .map_err(|error| error.to_string())?;
        let tile_height = decoder
            .get_tag_unsigned::<usize>(Tag::TileLength)
            .map_err(|error| error.to_string())?;
        let tile_pixels = tile_width
            .checked_mul(tile_height)
            .ok_or_else(|| "TIFF tile area overflowed".to_owned())?;
        if tile_pixels == 0 {
            return Err("TIFF tile dimensions must be nonzero".to_owned());
        }
        Ok((tile_pixels <= MAX_TILE_PIXELS).then(|| Self {
            width,
            height,
            tile_width,
            tile_height,
            columns: width.div_ceil(tile_width),
        }))
    }

    /// Copy the available columns of a tile into the interleaved float output.
    ///
    /// # Errors
    ///
    /// Reports invalid tile dimensions, strides or decoded sample type and extent.
    fn read_tile(
        &self,
        decoder: &mut Decoder<TileInput<'_>>,
        scratch: &mut DecodingResult,
        samples: &mut [f32],
        index: usize,
    ) -> Result<(), String> {
        let rgb_stride = rgb_samples(self.width)?;
        let column = index
            .checked_rem(self.columns)
            .and_then(|column| column.checked_mul(self.tile_width))
            .ok_or_else(|| "TIFF tile column overflowed".to_owned())?;
        let row = index
            .checked_div(self.columns)
            .and_then(|row| row.checked_mul(self.tile_height))
            .ok_or_else(|| "TIFF tile row overflowed".to_owned())?;
        let width = self.width.saturating_sub(column).min(self.tile_width);
        let height = self.height.saturating_sub(row).min(self.tile_height);
        let start = rgb_samples(column)?;
        let tile_stride = rgb_samples(width)?;
        let tile_bytes = tile_stride
            .checked_mul(size_of::<u16>())
            .ok_or_else(|| "TIFF tile stride overflowed".to_owned())?;
        let chunk = u32::try_from(index).map_err(|error| error.to_string())?;
        decoder
            .read_chunk_to_buffer(scratch, chunk, tile_bytes)
            .map_err(|error| format!("TIFF tile {index}: {error}"))?;
        let DecodingResult::U16(codes) = scratch else {
            return Err("TIFF tile sample type changed".to_owned());
        };
        if codes.len() != height.saturating_mul(tile_stride) {
            return Err("TIFF tile decoded sample count changed".to_owned());
        }
        for (output, native) in samples
            .chunks_exact_mut(rgb_stride)
            .skip(row)
            .zip(codes.chunks_exact(tile_stride))
        {
            let target = output
                .get_mut(start..start.saturating_add(tile_stride))
                .ok_or_else(|| "TIFF tile output lies outside its raster".to_owned())?;
            for (sample, &code) in target.iter_mut().zip(native) {
                *sample = f32::from(code) / f32::from(u16::MAX);
            }
        }
        Ok(())
    }
}

/// Convert a pixel count or row width to interleaved RGB elements.
///
/// # Errors
///
/// Rejects a count that cannot hold three samples per pixel.
fn rgb_samples(pixels: usize) -> Result<usize, String> {
    pixels
        .checked_mul(3)
        .ok_or_else(|| "TIFF RGB sample count overflowed".to_owned())
}

/// Stream the eligible tiled TIFF directly to normalized working samples.
///
/// # Errors
///
/// Rejects invalid dimensions, truncated or invalid compressed ranges and decode errors.
pub(super) fn decode(input: &mut BufReader<File>) -> Result<Option<RgbImage>, String> {
    let source_len = input
        .get_ref()
        .metadata()
        .map_err(|error| error.to_string())?
        .len();
    let span = Cell::new(None);
    let stream = TileInput {
        input,
        position: 0,
        span: &span,
    };
    let Ok(mut decoder) = Decoder::new(stream) else {
        return Ok(None);
    };
    if !supports_streaming(&mut decoder) {
        return Ok(None);
    }
    let Some(layout) = Layout::read(&mut decoder)? else {
        return Ok(None);
    };
    let offsets = decoder
        .get_tag_u64_vec(Tag::TileOffsets)
        .map_err(|error| error.to_string())?;
    let counts = decoder
        .get_tag_u64_vec(Tag::TileByteCounts)
        .map_err(|error| error.to_string())?;
    let tiles = layout
        .columns
        .saturating_mul(layout.height.div_ceil(layout.tile_height));
    if offsets.len() != tiles || counts.len() != tiles {
        return Err("TIFF tile directory size does not match the image".to_owned());
    }
    let spans = offsets
        .into_iter()
        .zip(counts)
        .map(|(offset, count)| {
            offset
                .checked_add(count)
                .filter(|&end| count != 0 && end <= source_len)
                .map(|end| (offset, end))
                .ok_or_else(|| "compressed TIFF tile lies outside the source file".to_owned())
        })
        .collect::<Result<Vec<_>, String>>()?;

    let pixels = checked_pixel_count(layout.width, layout.height)?;
    let mut samples = vec![0.0_f32; rgb_samples(pixels)?];
    let mut scratch = DecodingResult::U16(Vec::new());
    for (index, extent) in spans.into_iter().enumerate() {
        span.set(Some(extent));
        layout.read_tile(&mut decoder, &mut scratch, &mut samples, index)?;
    }
    span.set(None);
    let mut frame = RgbImage::new(layout.width, layout.height, samples)?;
    frame.sample_encoding = SampleEncoding::U16;
    frame.icc_profile = profile_from_tiff(decoder);
    Ok(Some(frame))
}
