import Foundation
import UIKit
import Photos
import AVFoundation

// Saves photos and videos from the live stream to the iPhone's Camera Roll.
@Observable
final class PhotosManager {

    private var assetWriter: AVAssetWriter?
    private var writerInput: AVAssetWriterInput?
    private var pixelAdaptor: AVAssetWriterInputPixelBufferAdaptor?
    private var recordingURL: URL?
    private var frameIndex: Int64 = 0
    private let fps: Int32 = 8

    // MARK: - Photo

    func savePhoto(_ image: UIImage) {
        requestAccess {
            PHPhotoLibrary.shared().performChanges {
                PHAssetCreationRequest.forAsset().addResource(
                    with: .photo,
                    data: image.jpegData(compressionQuality: 0.92)!,
                    options: nil
                )
            }
        }
    }

    // MARK: - Video recording

    func startRecording() {
        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent(UUID().uuidString)
            .appendingPathExtension("mp4")
        recordingURL = url
        frameIndex = 0

        guard let writer = try? AVAssetWriter(outputURL: url, fileType: .mp4) else { return }

        let settings: [String: Any] = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: 640,
            AVVideoHeightKey: 480,
        ]
        let input = AVAssetWriterInput(mediaType: .video, outputSettings: settings)
        input.expectsMediaDataInRealTime = true

        let adaptor = AVAssetWriterInputPixelBufferAdaptor(
            assetWriterInput: input,
            sourcePixelBufferAttributes: [
                kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
                kCVPixelBufferWidthKey as String: 640,
                kCVPixelBufferHeightKey as String: 480,
            ]
        )

        writer.add(input)
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)

        assetWriter = writer
        writerInput = input
        pixelAdaptor = adaptor
    }

    func appendFrame(_ image: UIImage) {
        guard let input = writerInput, input.isReadyForMoreMediaData,
              let adaptor = pixelAdaptor,
              let pixelBuffer = image.toPixelBuffer(width: 640, height: 480) else { return }

        let time = CMTime(value: frameIndex, timescale: fps)
        adaptor.append(pixelBuffer, withPresentationTime: time)
        frameIndex += 1
    }

    func stopRecording() {
        writerInput?.markAsFinished()
        assetWriter?.finishWriting { [weak self] in
            guard let self, let url = self.recordingURL else { return }
            self.requestAccess {
                PHPhotoLibrary.shared().performChanges {
                    PHAssetCreationRequest.forAsset().addResource(with: .video,
                                                                  fileURL: url,
                                                                  options: nil)
                }
            }
        }
        assetWriter = nil
        writerInput = nil
        pixelAdaptor = nil
        recordingURL = nil
    }

    // MARK: - Permission

    private func requestAccess(then block: @escaping () -> Void) {
        let status = PHPhotoLibrary.authorizationStatus(for: .addOnly)
        switch status {
        case .authorized, .limited:
            block()
        case .notDetermined:
            PHPhotoLibrary.requestAuthorization(for: .addOnly) { granted in
                if granted == .authorized || granted == .limited { block() }
            }
        default:
            break
        }
    }
}

// MARK: - UIImage → CVPixelBuffer

private extension UIImage {
    func toPixelBuffer(width: Int, height: Int) -> CVPixelBuffer? {
        var buffer: CVPixelBuffer?
        let attrs: [String: Any] = [
            kCVPixelBufferCGImageCompatibilityKey as String: true,
            kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
        ]
        guard CVPixelBufferCreate(kCFAllocatorDefault, width, height,
                                   kCVPixelFormatType_32ARGB,
                                   attrs as CFDictionary, &buffer) == kCVReturnSuccess,
              let pb = buffer else { return nil }

        CVPixelBufferLockBaseAddress(pb, [])
        defer { CVPixelBufferUnlockBaseAddress(pb, []) }

        let ctx = CGContext(data: CVPixelBufferGetBaseAddress(pb),
                            width: width, height: height,
                            bitsPerComponent: 8,
                            bytesPerRow: CVPixelBufferGetBytesPerRow(pb),
                            space: CGColorSpaceCreateDeviceRGB(),
                            bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)
        ctx?.draw(cgImage!, in: CGRect(x: 0, y: 0, width: width, height: height))
        return pb
    }
}
