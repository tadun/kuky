import Foundation
import UIKit

// Connects to the robot's MJPEG stream and WebSocket control endpoint.
@Observable
final class RobotClient: NSObject {

    // MARK: - Published state

    var latestFrame: UIImage?
    var isConnected = false
    var mode: String = "auto"          // "manual" | "auto"
    var distanceCM: Double = 999
    var lastAction: String = "STOP"

    // MARK: - Config

    let host: String
    let port: Int

    // MARK: - Private

    private var streamSession: URLSession!
    private var streamTask: URLSessionDataTask?
    private var wsTask: URLSessionWebSocketTask?

    // Rolling byte buffer for MJPEG frame extraction
    private var buffer = Data()
    private let frameBoundary = Data("--frame\r\n".utf8)
    private let headerSeparator = Data("\r\n\r\n".utf8)

    init(host: String = "kuky.local", port: Int = 8765) {
        self.host = host
        self.port = port
        super.init()
        streamSession = URLSession(configuration: .default,
                                   delegate: self,
                                   delegateQueue: .main)
    }

    // MARK: - Lifecycle

    func connect() {
        startStream()
        startWebSocket()
    }

    func disconnect() {
        streamTask?.cancel()
        wsTask?.cancel(with: .goingAway, reason: nil)
        isConnected = false
    }

    // MARK: - MJPEG stream

    private func startStream() {
        let url = URL(string: "http://\(host):\(port)/stream")!
        streamTask = streamSession.dataTask(with: url)
        streamTask?.resume()
    }

    // MARK: - WebSocket

    private func startWebSocket() {
        let url = URL(string: "ws://\(host):\(port)/ws")!
        wsTask = URLSession.shared.webSocketTask(with: url)
        wsTask?.resume()
        receiveNextMessage()
    }

    private func receiveNextMessage() {
        wsTask?.receive { [weak self] result in
            guard let self else { return }
            if case .success(let msg) = result,
               case .string(let text) = msg,
               let data = text.data(using: .utf8),
               let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                Task { @MainActor in
                    self.handleTelemetry(json)
                }
            }
            self.receiveNextMessage()
        }
    }

    private func handleTelemetry(_ json: [String: Any]) {
        if let m = json["mode"] as? String { mode = m }
        if let d = json["distance_cm"] as? Double { distanceCM = d }
        if let a = json["action"] as? String { lastAction = a }
        if json["type"] as? String == "state" { isConnected = true }
        if json["type"] as? String == "telemetry" { isConnected = true }
    }

    // MARK: - Commands

    func sendMove(_ dir: String) {
        send(["type": "move", "dir": dir])
    }

    func sendMode(_ value: String) {
        mode = value
        send(["type": "mode", "value": value])
    }

    private func send(_ payload: [String: String]) {
        guard let data = try? JSONSerialization.data(withJSONObject: payload),
              let text = String(data: data, encoding: .utf8) else { return }
        wsTask?.send(.string(text)) { _ in }
    }
}

// MARK: - URLSessionDataDelegate (MJPEG parsing)

extension RobotClient: URLSessionDataDelegate {

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask,
                    didReceive response: URLResponse,
                    completionHandler: @escaping (URLSession.ResponseDisposition) -> Void) {
        completionHandler(.allow)
    }

    func urlSession(_ session: URLSession, dataTask: URLSessionDataTask,
                    didReceive data: Data) {
        buffer.append(data)
        extractFrames()
    }

    func urlSession(_ session: URLSession, task: URLSessionTask,
                    didCompleteWithError error: Error?) {
        // Reconnect on stream drop (unless cancelled intentionally)
        guard (error as? URLError)?.code != .cancelled else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            self?.startStream()
        }
    }

    private func extractFrames() {
        // Keep processing as long as we can find a complete frame
        while true {
            guard let boundaryRange = buffer.range(of: frameBoundary) else { break }
            let afterBoundary = boundaryRange.upperBound
            guard let headerEnd = buffer.range(of: headerSeparator, in: afterBoundary...) else { break }

            let jpegStart = headerEnd.upperBound
            // Look for the next boundary to delimit the end of the JPEG
            guard let nextBoundary = buffer.range(of: frameBoundary, in: jpegStart...) else { break }

            // Strip the trailing \r\n that precedes the next --frame
            let jpegEnd = nextBoundary.lowerBound - 2
            guard jpegEnd > jpegStart else {
                buffer = Data(buffer[nextBoundary.lowerBound...])
                continue
            }

            let jpegData = buffer[jpegStart..<jpegEnd]
            if let image = UIImage(data: jpegData) {
                latestFrame = image
                isConnected = true
            }
            buffer = Data(buffer[nextBoundary.lowerBound...])
        }
        // Prevent unbounded growth if boundary is never found
        if buffer.count > 2_000_000 { buffer.removeAll() }
    }
}
