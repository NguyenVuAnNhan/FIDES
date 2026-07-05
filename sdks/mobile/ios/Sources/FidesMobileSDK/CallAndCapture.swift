import AVFoundation
import CallKit
import UIKit
    public let activeCall: Bool
    public let callerType: String
    public let callerNumber: String

    public init(activeCall: Bool, callerType: String = "unknown", callerNumber: String = "") {
        self.activeCall = activeCall
        self.callerType = callerType
        self.callerNumber = callerNumber
    }

    public static let idle = CallContext(activeCall: false)
}

public protocol CallStateMonitor {
    func snapshot() -> CallContext
}

public extension ShieldTransaction {
    func withCallContext(_ context: CallContext) -> ShieldTransaction {
        var copy = self
        copy.activeCall = context.activeCall
        copy.callerType = context.callerType
        copy.callerNumber = context.callerNumber
        return copy
    }
}

public final class IosCallStateMonitor: CallStateMonitor {
    private let callObserver = CXCallObserver()

    public init() {}

    public func snapshot() -> CallContext {
        let active = callObserver.calls.contains { !$0.hasEnded }
        guard active else {
            return .idle
        }
        return CallContext(
            activeCall: true,
            callerType: "unknown",
            callerNumber: ""
        )
    }
}

public struct LiveCheckCaptureConfig {
    public let durationSeconds: Int
    public let frameCount: Int

    public init(durationSeconds: Int = 10, frameCount: Int = 3) {
        self.durationSeconds = durationSeconds
        self.frameCount = frameCount
    }
}

public struct LiveCheckCaptureResult {
    public let videoData: Data
    public let videoFilename: String
    public let videoContentType: String
    public let frames: [LiveCheckFramePart]

    public init(
        videoData: Data,
        videoFilename: String,
        videoContentType: String = "video/mp4",
        frames: [LiveCheckFramePart]
    ) {
        self.videoData = videoData
        self.videoFilename = videoFilename
        self.videoContentType = videoContentType
        self.frames = frames
    }
}

public extension LiveCheckCaptureResult {
    func toUploadInput(documentData: Data, documentFilename: String, documentContentType: String = "image/jpeg") -> LiveCheckUploadInput {
        LiveCheckUploadInput(
            challengeVideo: videoData,
            challengeVideoFilename: videoFilename,
            challengeVideoContentType: videoContentType,
            document: documentData,
            documentFilename: documentFilename,
            documentContentType: documentContentType,
            frames: frames
        )
    }
}

/// Minimal live-check capture stub. Host apps should wire AVCaptureSession or provide bytes manually.
public enum LiveCheckCapture {
    public static func extractJpegFrames(fromVideoAt url: URL, frameCount: Int) throws -> [LiveCheckFramePart] {
        let asset = AVURLAsset(url: url)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        let duration = CMTimeGetSeconds(asset.duration)
        guard duration.isFinite, duration > 0 else {
            return []
        }

        var frames: [LiveCheckFramePart] = []
        for index in 0..<frameCount {
            let timestamp = duration * Double(index + 1) / Double(frameCount + 1)
            let time = CMTime(seconds: timestamp, preferredTimescale: 600)
            let image = try generator.copyCGImage(at: time, actualTime: nil)
            let data = UIImage(cgImage: image).jpegData(compressionQuality: 0.9) ?? Data()
            frames.append(LiveCheckFramePart(index: index, jpegData: data))
        }
        return frames
    }
}
