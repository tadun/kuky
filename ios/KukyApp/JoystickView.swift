import SwiftUI

// D-pad joystick: sends directional commands on press, "stop" on release.
struct JoystickView: View {
    var onMove: (String) -> Void

    var body: some View {
        VStack(spacing: 4) {
            dpadButton(dir: "forward",  icon: "arrow.up")
            HStack(spacing: 4) {
                dpadButton(dir: "left",  icon: "arrow.left")
                stopButton
                dpadButton(dir: "right", icon: "arrow.right")
            }
            dpadButton(dir: "backward", icon: "arrow.down")
        }
    }

    private func dpadButton(dir: String, icon: String) -> some View {
        DragButton(size: 52) {
            onMove(dir)
        } onRelease: {
            onMove("stop")
        } label: {
            Image(systemName: icon)
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(.white)
        }
    }

    private var stopButton: some View {
        Button {
            onMove("stop")
        } label: {
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.white.opacity(0.15))
                .frame(width: 52, height: 52)
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(.white.opacity(0.3), lineWidth: 1)
                )
        }
    }
}

// Button that fires on press-down and stops on release.
private struct DragButton<Label: View>: View {
    let size: CGFloat
    let onPress: () -> Void
    let onRelease: () -> Void
    @ViewBuilder let label: Label

    @State private var isPressed = false

    var body: some View {
        label
            .frame(width: size, height: size)
            .background(
                RoundedRectangle(cornerRadius: 10)
                    .fill(isPressed
                          ? Color.white.opacity(0.35)
                          : Color.white.opacity(0.15))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 10)
                    .strokeBorder(.white.opacity(0.3), lineWidth: 1)
            )
            .gesture(
                DragGesture(minimumDistance: 0)
                    .onChanged { _ in
                        if !isPressed {
                            isPressed = true
                            onPress()
                        }
                    }
                    .onEnded { _ in
                        isPressed = false
                        onRelease()
                    }
            )
    }
}
