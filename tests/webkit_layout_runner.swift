// Execute the synthetic deck-list fixture in the system WebKit view.
import AppKit
import WebKit

final class Navigation: NSObject, WKNavigationDelegate {
    let script: String
    init(script: String) { self.script = script }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        webView.evaluateJavaScript(script) { value, error in
            if let error = error {
                fputs("\(error)\n", stderr)
                exit(1)
            }
            print(value ?? "null")
            NSApplication.shared.terminate(nil)
        }
    }
}

let width = Double(CommandLine.arguments[1])!
let html = try String(contentsOfFile: CommandLine.arguments[2], encoding: .utf8)
let script = try String(contentsOfFile: CommandLine.arguments[3], encoding: .utf8)
let app = NSApplication.shared
let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: width, height: 520),
                      styleMask: [.titled], backing: .buffered, defer: false)
let web = WKWebView(frame: window.contentView!.bounds)
let navigation = Navigation(script: script)
web.navigationDelegate = navigation
window.contentView!.addSubview(web)
window.makeKeyAndOrderFront(nil)
web.loadHTMLString(html, baseURL: nil)
app.run()
