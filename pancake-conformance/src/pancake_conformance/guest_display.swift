// Set and verify the guest's remembered mode, independently of Tart's display size.
import Foundation
import CoreGraphics

let display = CGMainDisplayID()
let options = [kCGDisplayShowDuplicateLowResolutionModes: true] as CFDictionary
let modes = CGDisplayCopyAllDisplayModes(display, options) as? [CGDisplayMode] ?? []
guard let wanted = modes.first(where: {
    $0.width == 1440 && $0.height == 1000 && $0.pixelWidth == 2880 && $0.pixelHeight == 2000
}) else {
    fputs("Guest lacks 1440x1000 Retina display mode\n", stderr)
    exit(1)
}
if !CommandLine.arguments.contains("--check") {
    var configuration: CGDisplayConfigRef?
    guard CGBeginDisplayConfiguration(&configuration) == .success else { exit(1) }
    guard CGConfigureDisplayWithDisplayMode(configuration, display, wanted, nil) == .success else {
        CGCancelDisplayConfiguration(configuration)
        exit(1)
    }
    guard CGCompleteDisplayConfiguration(configuration, .permanently) == .success else {
        fputs("Could not save guest display mode\n", stderr)
        exit(1)
    }
}
guard let actual = CGDisplayCopyDisplayMode(display) else { exit(1) }
let result = ["width": actual.width, "height": actual.height,
              "pixel_width": actual.pixelWidth, "pixel_height": actual.pixelHeight]
let data = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
