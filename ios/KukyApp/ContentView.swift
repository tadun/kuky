import SwiftUI
import Photos

struct ContentView: View {
    @Environment(RobotClient.self) private var client
    @State private var photosManager = PhotosManager()
    @State private var isRecording = false

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            // Live stream
            StreamView()

            // Control overlay
            VStack {
                topBar
                Spacer()
                bottomBar
            }
            .padding()
        }
        .statusBarHidden()
        .onAppear { client.connect() }
        .onDisappear { client.disconnect() }
        .onChange(of: client.latestFrame) { _, frame in
            if isRecording, let frame { photosManager.appendFrame(frame) }
        }
    }

    // MARK: - Top bar

    private var topBar: some View {
        HStack {
            modeToggle
            Spacer()
            telemetryBadge
        }
    }

    private var modeToggle: some View {
        Button {
            client.sendMode(client.mode == "auto" ? "manual" : "auto")
        } label: {
            Text(client.mode.uppercased())
                .font(.system(.caption, design: .monospaced, weight: .bold))
                .foregroundStyle(client.mode == "manual" ? Color.orange : Color.green)
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(.ultraThinMaterial, in: Capsule())
        }
    }

    private var telemetryBadge: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(client.isConnected ? Color.green : Color.red)
                .frame(width: 8, height: 8)
            Text(client.isConnected
                 ? "\(client.lastAction) · \(Int(client.distanceCM)) cm"
                 : "Connecting…")
                .font(.system(.caption, design: .monospaced))
                .foregroundStyle(.white)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .background(.ultraThinMaterial, in: Capsule())
    }

    // MARK: - Bottom bar

    private var bottomBar: some View {
        VStack(alignment: .trailing, spacing: 8) {
            if client.mode == "manual" {
                speedSlider
            }
            HStack(alignment: .bottom) {
                captureButtons
                Spacer()
                JoystickView { dir in
                    client.sendMove(dir)
                }
            }
        }
    }

    private var speedSlider: some View {
        HStack(spacing: 10) {
            Image(systemName: "tortoise.fill")
                .foregroundStyle(.white.opacity(0.6))
            Slider(value: Binding(
                get: { client.speed },
                set: { client.sendSpeed($0) }
            ), in: 0.2...1.0, step: 0.1)
            .tint(.orange)
            Image(systemName: "hare.fill")
                .foregroundStyle(.white.opacity(0.6))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 10))
    }

    private var captureButtons: some View {
        VStack(spacing: 12) {
            // Video record button
            Button {
                toggleRecording()
            } label: {
                Image(systemName: isRecording ? "stop.circle.fill" : "record.circle")
                    .font(.system(size: 36))
                    .foregroundStyle(isRecording ? Color.red : Color.white)
                    .shadow(radius: 4)
            }

            // Photo button
            Button {
                takePhoto()
            } label: {
                Image(systemName: "camera.circle.fill")
                    .font(.system(size: 36))
                    .foregroundStyle(.white)
                    .shadow(radius: 4)
            }
        }
    }

    // MARK: - Actions

    private func takePhoto() {
        guard let frame = client.latestFrame else { return }
        photosManager.savePhoto(frame)
    }

    private func toggleRecording() {
        if isRecording {
            photosManager.stopRecording()
            isRecording = false
        } else {
            photosManager.startRecording()
            isRecording = true
        }
    }
}

// MARK: - Stream view

struct StreamView: View {
    @Environment(RobotClient.self) private var client

    var body: some View {
        Group {
            if let frame = client.latestFrame {
                Image(uiImage: frame)
                    .resizable()
                    .scaledToFit()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                VStack(spacing: 12) {
                    ProgressView()
                        .tint(.white)
                    Text("Connecting to robot\u{2026}")
                        .font(.system(.caption, design: .monospaced))
                        .foregroundStyle(.white.opacity(0.6))
                }
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
