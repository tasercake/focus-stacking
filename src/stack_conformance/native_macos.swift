// JSON-lines transport over macOS Accessibility and native input APIs.
import Foundation
import AppKit
import ApplicationServices
import Darwin

struct UIError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) { self.description = description }
}
func attribute(_ element: AXUIElement, _ name: String) -> CFTypeRef? {
    var result: CFTypeRef?
    return AXUIElementCopyAttributeValue(element, name as CFString, &result) == .success ? result : nil
}
func string(_ value: CFTypeRef?) -> String {
    guard let value = value else { return "" }
    if CFGetTypeID(value) == CFURLGetTypeID() { return CFURLGetString(unsafeBitCast(value,to:CFURL.self)) as String }
    return (value as? String) ?? ""
}
func children(_ element: AXUIElement) -> [AXUIElement] {
    var result = (attribute(element, "AXChildren") as? [AXUIElement]) ?? []
    for name in (string(attribute(element, "AXRole")) == "AXWindow" ? ["AXSheets"] : []) {
        for child in (attribute(element, name) as? [AXUIElement]) ?? [] {
            if !result.contains(where: { CFEqual($0, child) }) { result.append(child) }
        }
    }
    return result
}
func numeric(_ value: CFTypeRef?) -> Any? {
    guard let value = value else { return nil }
    if let number = value as? NSNumber { return number }
    if let text = value as? String { return text }
    return nil
}
func point(_ element: AXUIElement) -> CGPoint? {
    guard let raw = attribute(element, "AXPosition"), CFGetTypeID(raw) == AXValueGetTypeID() else { return nil }
    var result = CGPoint.zero
    return AXValueGetValue(unsafeBitCast(raw, to: AXValue.self), .cgPoint, &result) ? result : nil
}
func size(_ element: AXUIElement) -> CGSize? {
    guard let raw = attribute(element, "AXSize"), CFGetTypeID(raw) == AXValueGetTypeID() else { return nil }
    var result = CGSize.zero
    return AXValueGetValue(unsafeBitCast(raw, to: AXValue.self), .cgSize, &result) ? result : nil
}
func describe(_ element: AXUIElement, _ path: [Int]) -> [String: Any] {
    var result: [String: Any] = ["path": path]
    for (key, name) in [("id", "AXIdentifier"), ("role", "AXRole"), ("subrole", "AXSubrole"), ("title", "AXTitle"), ("description", "AXDescription"), ("help", "AXHelp")] {
        let text = string(attribute(element, name))
        if !text.isEmpty { result[key] = text }
    }
    for (key, name) in [("value", "AXValue"), ("enabled", "AXEnabled"), ("selected", "AXSelected"), ("focused", "AXFocused")] {
        if let value = numeric(attribute(element, name)) { result[key] = value }
    }
    if let p = point(element) { result["position"] = [p.x, p.y] }
    if let s = size(element) { result["size"] = [s.width, s.height] }
    return result
}
func flatten(_ root: AXUIElement) -> [(AXUIElement, [String: Any])] {
    var result: [(AXUIElement, [String: Any])] = []
    var seen: [AXUIElement] = []
    func walk(_ element: AXUIElement, _ path: [Int], _ depth: Int) {
        if depth > 32 || result.count >= 6000 || seen.contains(where: { CFEqual($0, element) }) { return }
        seen.append(element)
        result.append((element, describe(element, path)))
        // File browsers virtualize arbitrary directory trees. Read their controls, not file contents.
        let role = string(attribute(element, "AXRole"))
        if role == "AXOutline" || role == "AXBrowser" { return }
        for (index, child) in children(element).enumerated() {
            // The system Apple menu is not part of the target application.
            if string(attribute(child, "AXRole")) == "AXMenuBarItem" && string(attribute(child, "AXTitle")) == "Apple" { continue }
            walk(child, path + [index], depth + 1)
        }
    }
    walk(root, [], 0)
    return result
}
func matches(_ row: [String: Any], _ selector: [String: Any]) -> Bool {
    for (key, wanted) in selector {
        if key == "path" {
            if (row[key] as? [Int]) != (wanted as? [Int]) { return false }
        } else if String(describing: row[key] ?? "") != String(describing: wanted) { return false }
    }
    return true
}
func locate(_ root: AXUIElement, _ selector: [String: Any]) throws -> AXUIElement {
    guard !selector.isEmpty else { return root }
    if let path = selector["path"] as? [Int] {
        var element = root
        for index in path {
            let candidates = children(element)
            guard index >= 0 && index < candidates.count else { throw UIError("Accessibility path is stale") }
            element = candidates[index]
        }
        return element
    }
    guard let row = flatten(root).first(where: { matches($0.1, selector) }) else { throw UIError("No accessibility element matches \(selector)") }
    return row.0
}
func flags(_ names: [String]) -> CGEventFlags {
    var value = CGEventFlags()
    for name in names {
        switch name.lowercased() {
        case "command", "cmd": value.insert(.maskCommand)
        case "shift": value.insert(.maskShift)
        case "control", "ctrl": value.insert(.maskControl)
        case "option", "alt": value.insert(.maskAlternate)
        default: break
        }
    }
    return value
}
let keyCodes: [String: CGKeyCode] = ["a":0,"s":1,"d":2,"f":3,"h":4,"g":5,"z":6,"x":7,"c":8,"v":9,"b":11,"q":12,"w":13,"e":14,"r":15,"y":16,"t":17,"1":18,"2":19,"3":20,"4":21,"6":22,"5":23,"=":24,"9":25,"7":26,"-":27,"8":28,"0":29,"o":31,"u":32,"i":34,"p":35,"return":36,"enter":36,"l":37,"j":38,"'":39,"k":40,";":41,"\\":42,",":43,"/":44,"n":45,"m":46,".":47,"tab":48,"space":49,"delete":51,"escape":53,"home":115,"end":119,"left":123,"right":124,"down":125,"up":126]
func key(_ name: String, _ modifiers: [String]) throws {
    guard let code = keyCodes[name.lowercased()] else { throw UIError("Unknown key: \(name)") }
    let modifierNames = modifiers.compactMap { value -> String? in
        switch value.lowercased() {
        case "command", "cmd": return "command down"
        case "shift": return "shift down"
        case "control", "ctrl": return "control down"
        case "option", "alt": return "option down"
        default: return nil
        }
    }
    let suffix = modifierNames.isEmpty ? "" : " using {" + modifierNames.joined(separator:", ") + "}"
    let process = Process(); process.executableURL = URL(fileURLWithPath:"/usr/bin/osascript")
    let action: String
    if name.count == 1 {
        let escaped = name.replacingOccurrences(of:"\\",with:"\\\\").replacingOccurrences(of:"\"",with:"\\\"")
        action = "keystroke \"" + escaped + "\""
    } else { action = "key code \(code)" }
    process.arguments = ["-e", "tell application \"System Events\" to " + action + suffix]
    let errors = Pipe(); process.standardError = errors
    try process.run()
    let deadline = Date(timeIntervalSinceNow: 8)
    while process.isRunning && Date() < deadline { RunLoop.current.run(until:Date(timeIntervalSinceNow:0.02)) }
    if process.isRunning {
        process.terminate()
        let stopDeadline = Date(timeIntervalSinceNow: 1)
        while process.isRunning && Date() < stopDeadline { RunLoop.current.run(until:Date(timeIntervalSinceNow:0.02)) }
        if process.isRunning { kill(process.processIdentifier,SIGKILL) }
        process.waitUntilExit()
        throw UIError("Native keyboard input timed out; allow Automation access to System Events")
    }
    process.waitUntilExit()
    guard process.terminationStatus == 0 else {
        let message = String(data:errors.fileHandleForReading.readDataToEndOfFile(),encoding:.utf8) ?? ""
        throw UIError("Native keyboard input failed; allow Automation access to System Events: " + message)
    }
}
// One retained state table keeps matching button down/up and drag events coherent.
let inputSource = CGEventSource(stateID: .privateState)

func typeText(_ text: String) throws {
    let source = inputSource
    for scalar in text {
        let units = Array(String(scalar).utf16)
        for down in [true, false] {
            guard let event = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: down) else { throw UIError("Cannot create text event") }
            event.flags = []
            event.keyboardSetUnicodeString(stringLength: units.count, unicodeString: units)
            event.post(tap: .cghidEventTap)
        }
    }
}
func pointer(_ point: CGPoint, _ type: CGEventType) {
    let source = inputSource
    let event = CGEvent(mouseEventSource: source, mouseType: type, mouseCursorPosition: point, mouseButton: .left)
    event?.flags = []
    event?.post(tap: .cghidEventTap)
}
func center(_ element: AXUIElement, _ relative: [Double] = [0.5,0.5]) throws -> CGPoint {
    guard let p = point(element), let s = size(element) else { throw UIError("Element has no screen rectangle") }
    return CGPoint(x: p.x+s.width*relative[0], y: p.y+s.height*relative[1])
}
func execute(_ request: [String: Any]) throws -> Any {
    let command = request["command"] as? String ?? ""
    if command == "trust" { return ["trusted": AXIsProcessTrusted()] }
    if !["snapshot","press","click","focus","set","key","text","drag","scroll","screenshot","raise","attributes"].contains(command) { throw UIError("Unknown command: \(command)") }
    guard AXIsProcessTrusted() else { throw UIError("Accessibility permission is required for native UI tests") }
    guard let pid = request["pid"] as? Int, pid > 0, kill(pid_t(pid),0) == 0 else { throw UIError("Target application is not running") }
    let app = NSRunningApplication(processIdentifier:pid_t(pid))
    let root = AXUIElementCreateApplication(pid_t(pid))
    if command == "snapshot" { return ["pid":pid, "nodes":flatten(root).map{$0.1}] }
    if !["set", "focus", "screenshot", "attributes"].contains(command) && NSWorkspace.shared.frontmostApplication?.processIdentifier != pid_t(pid) {
        if command == "key" || command == "text" { throw UIError("Target application is not frontmost; keyboard input was not sent") }
        _ = app?.activate(options: [.activateIgnoringOtherApps])
        // Command-line GUI executables can decline NSRunningApplication activation.
        // Raise and focus their frontmost native window with a real title-bar click.
        if let window = children(root).first(where: { string(attribute($0,"AXRole")) == "AXWindow" }), let p = point(window), let s = size(window) {
            _ = AXUIElementPerformAction(window,"AXRaise" as CFString)
            let titlePoint = CGPoint(x:p.x+s.width*0.5,y:p.y+12)
            pointer(titlePoint,.mouseMoved); pointer(titlePoint,.leftMouseDown); pointer(titlePoint,.leftMouseUp)
        }
        let activationDeadline = Date(timeIntervalSinceNow: 3)
        while NSWorkspace.shared.frontmostApplication?.processIdentifier != pid_t(pid) && Date() < activationDeadline {
            RunLoop.current.run(until: Date(timeIntervalSinceNow: 0.02))
        }
        guard NSWorkspace.shared.frontmostApplication?.processIdentifier == pid_t(pid) else { throw UIError("Target application did not become frontmost; input was not sent") }
    }
    if command == "raise" { return ["raised":true] }
    if command == "key" { try key(request["key"] as? String ?? "", request["modifiers"] as? [String] ?? []); return ["sent":true] }
    if command == "text" { try typeText(request["text"] as? String ?? ""); return ["sent":true] }
    if command == "screenshot" {
        guard let destination = request["path"] as? String else { throw UIError("Screenshot requires path") }
        guard let windows = CGWindowListCopyWindowInfo(.optionOnScreenOnly,kCGNullWindowID) as? [[String:Any]],
              let window = windows.first(where: { ($0[kCGWindowOwnerPID as String] as? Int) == pid && ($0[kCGWindowLayer as String] as? Int) == 0 }),
              let number = window[kCGWindowNumber as String] as? Int else { throw UIError("Target has no on-screen window to capture") }
        let process = Process(); process.executableURL = URL(fileURLWithPath: "/usr/sbin/screencapture")
        process.arguments = ["-x", "-l", String(number), destination]; try process.run(); process.waitUntilExit()
        guard process.terminationStatus == 0 else { throw UIError("Screenshot failed; screen recording permission may be required") }
        return ["path":destination]
    }
    let selector = request["selector"] as? [String:Any] ?? [:]
    let element = try locate(root, selector)
    if command == "attributes" {
        var names: CFArray?
        guard AXUIElementCopyAttributeNames(element,&names) == .success else { throw UIError("Cannot read accessibility attributes") }
        var result: [String:Any] = [:]
        for name in (names as? [String]) ?? [] {
            let value = attribute(element,name)
            if let scalar = numeric(value) { result[name] = scalar }
            else { let text = string(value); if !text.isEmpty { result[name] = text } }
        }
        return result
    }
    if command == "focus" { let status = AXUIElementSetAttributeValue(element,"AXFocused" as CFString,kCFBooleanTrue); guard status == .success else { throw UIError("Focus failed: \(status.rawValue)") }; return ["focused":true] }
    if command == "set" {
        guard let value = request["value"] else { throw UIError("Set requires value") }
        let status = AXUIElementSetAttributeValue(element,"AXValue" as CFString,value as CFTypeRef)
        guard status == .success else { throw UIError("Set failed: \(status.rawValue)") }
        return ["set":true]
    }
    if command == "drag" {
        let start = try center(element,request["start"] as? [Double] ?? [0.5,0.5])
        let end = try center(element,request["end"] as? [Double] ?? [0.6,0.5])
        pointer(start,.mouseMoved); pointer(start,.leftMouseDown)
        for step in 1...12 { let fraction = Double(step)/12; pointer(CGPoint(x:start.x+(end.x-start.x)*fraction,y:start.y+(end.y-start.y)*fraction),.leftMouseDragged); Thread.sleep(forTimeInterval:0.012) }
        pointer(end,.leftMouseUp); return ["dragged":true]
    }
    if command == "scroll" {
        let p = try center(element); pointer(p,.mouseMoved)
        let dy = request["dy"] as? Int ?? 0
        let event = CGEvent(scrollWheelEvent2Source:inputSource,units:.pixel,wheelCount:1,wheel1:Int32(dy),wheel2:0,wheel3:0)
        event?.flags = []; event?.post(tap:.cghidEventTap)
        return ["scrolled":true]
    }
    if command == "press" {
        let status = AXUIElementPerformAction(element,"AXPress" as CFString)
        guard status == .success else { throw UIError("Press failed: \(status.rawValue)") }
    } else {
        let p = try center(element,request["position"] as? [Double] ?? [0.5,0.5])
        pointer(p,.mouseMoved); pointer(p,.leftMouseDown); Thread.sleep(forTimeInterval:0.03); pointer(p,.leftMouseUp)
    }
    return ["clicked":true]
}
while let line = readLine() {
    do {
        guard let data = line.data(using:.utf8), let request = try JSONSerialization.jsonObject(with:data) as? [String:Any] else { throw UIError("Request must be JSON object") }
        let result = try execute(request)
        let output = try JSONSerialization.data(withJSONObject:["ok":true,"result":result],options:[.sortedKeys])
        print(String(data:output,encoding:.utf8)!)
    } catch {
        let output = try! JSONSerialization.data(withJSONObject:["ok":false,"error":String(describing:error)],options:[.sortedKeys])
        print(String(data:output,encoding:.utf8)!)
    }
    fflush(stdout)
}
