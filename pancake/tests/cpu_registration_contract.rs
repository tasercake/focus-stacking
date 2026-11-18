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
