//! Run independent registration oracles through the production CPU backend.

include!("common/registration_cases.rs");

/// Recover known translation and crop coordinates, and reject featureless motion.
///
/// # Errors
///
/// Returns a device or numerical error.
#[test]
fn cpu_registration_geometry() -> Result<(), String> {
    let device = cubecl::Device::cpu().map_err(|error| error.to_string())?;
    crop_and_warp_preserve_rgb_coordinates(&device)?;
    registration_recovers_subpixel_translation(&device)?;
    featureless_pair_has_zero_confidence(&device)?;
    registration_recovers_wide_shift(&device)
}

/// Recover a real centered 3% expansion and cap the supported fit at 1%.
/// # Errors
/// Returns a device, geometry, confidence or scale error.
#[test]
fn cpu_breathing_clamps_a_supported_expansion() -> Result<(), String> {
    const WIDTH: u16 = 321;
    const HEIGHT: u16 = 257;
    const CENTER: [f32; 2] = [160.0, 128.0];
    const SCALE: f32 = 1.03;
    const INVERSE: f32 = 1.0 / SCALE;
    const BUDGET: usize = 16_777_216;
    let device = cubecl::Device::cpu().map_err(|error| error.to_string())?;
    let mut reference = Vec::new();
    let mut source = Vec::new();
    for y in (0..HEIGHT).map(f32::from) {
        for x in (0..WIDTH).map(f32::from) {
            reference.extend([scene_sample(x / 2.5, y / 2.5); 3]);
            let original_x = INVERSE.mul_add(x, (1.0 - INVERSE) * CENTER[0]);
            let original_y = INVERSE.mul_add(y, (1.0 - INVERSE) * CENTER[1]);
            source.extend([scene_sample(original_x / 2.5, original_y / 2.5); 3]);
        }
    }
    let prepare = |samples| {
        let [width, height] = [usize::from(WIDTH), usize::from(HEIGHT)];
        thumbnail(
            &device,
            Frame::new(width, height, samples)?,
            width,
            height,
            BUDGET,
        )
    };
    let reference = prepare(&reference)?;
    let source = prepare(&source)?;
    for (maximum, expected, tolerance) in [(0.05, SCALE, 0.002), (0.01, 1.01, 0.000_01)] {
        let estimated = estimate_pair(
            &device,
            &reference,
            &source,
            Model::Breathing,
            maximum,
            true,
        )?;
        let [[xx, xy, tx], [yx, yy, ty]] = estimated.transform.matrix();
        let center_x = xx.mul_add(CENTER[0], xy.mul_add(CENTER[1], tx));
        let center_y = yx.mul_add(CENTER[0], yy.mul_add(CENTER[1], ty));
        if !estimated.confidence.is_finite()
            || estimated.confidence <= 0.0
            || (center_x - CENTER[0])
                .abs()
                .max((center_y - CENTER[1]).abs())
                > 0.5
        {
            return Err(format!(
                "Breathing lost the supported centered fit at {maximum}: {estimated:?}"
            ));
        }
        if (xx - expected).abs().max((yy - expected).abs()) > tolerance {
            return Err(format!(
                "Breathing scale at limit {maximum} must be {expected}: {estimated:?}"
            ));
        }
    }
    Ok(())
}

/// An elongated reference canvas keeps aspect ratio within the thumbnail working budget.
///
/// # Errors
/// Returns a device error or an admission decision inconsistent with the packed proxy dimensions.
#[test]
fn cpu_panorama_thumbnail_respects_proxy_budget() -> Result<(), String> {
    // On an 8192 × 160 canvas, the bounded proxy is 3686 × 72 pixels.
    // Four working f32 samples per proxy pixel, two copies of the 12 input
    // samples and 32 fixed f32 scalars require exactly 4,246,496 bytes.
    const PROXY_BUDGET: usize = 4_246_496;
    let device = cubecl::Device::cpu().map_err(|error| error.to_string())?;
    let pixels = [0.5_f32; 12];
    let source = Frame::new(2, 2, &pixels)?;
    let below_budget = thumbnail(&device, source, 8192, 160, 4_246_495);
    if below_budget.err().as_deref() != Some("kernel working-data budget exceeded") {
        return Err("the panorama proxy must reject a budget one byte too small".to_owned());
    }
    let _proxy = thumbnail(&device, source, 8192, 160, PROXY_BUDGET).map_err(|error| {
        format!("the bounded panorama proxy must fit {PROXY_BUDGET} bytes: {error}")
    })?;
    Ok(())
}

/// Preserve every output sample when the final registration tile is partial.
/// # Errors
/// Returns an allocation, device, or sample mismatch error.
#[test]
fn cpu_registration_preserves_partial_final_tile() -> Result<(), String> {
    let (width, height) = (301, 293);
    let pixels = (0_u16..=u16::MAX)
        .cycle()
        .take(264_579)
        .map(f32::from)
        .collect::<Vec<_>>();
    let frame = Frame::new(width, height, &pixels)?;
    let bounds = Bounds::new(0, 0, width, height)?;
    let device = cubecl::Device::cpu().map_err(|error| error.to_string())?;
    let result = warp(&device, frame, Affine::IDENTITY, bounds, 8_388_608)?;
    if result != pixels {
        return Err("tiled registration did not preserve the complete RGB frame".to_owned());
    }
    Ok(())
}
