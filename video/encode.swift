// Turns video/build/frames (one JPEG per frame) and the narration in video/build/timeline.json into two MP4s:
// forager-demo-silent.mp4 (subtitles only) and forager-demo.mp4 (with the narration). Uses AVFoundation only.
// Usage: swiftc -O video/encode.swift -o video/build/encode && video/build/encode video/build

import AVFoundation
import CoreGraphics
import Foundation
import ImageIO

struct Clip: Decodable { let file: String; let start: Double }
struct Timeline: Decodable { let fps: Int32; let frames: Int; let duration: Double; let audio: [Clip] }

func fail(_ message: String) -> Never { FileHandle.standardError.write((message + "\n").data(using: .utf8)!); exit(1) }

let build = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "video/build")
let frames = build.appendingPathComponent("frames")
let timeline = try JSONDecoder().decode(Timeline.self, from: Data(contentsOf: build.appendingPathComponent("timeline.json")))
let silent = build.appendingPathComponent("forager-demo-silent.mp4")
let voiced = build.appendingPathComponent("forager-demo.mp4")

func image(_ url: URL) -> CGImage {
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { fail("cannot read \(url.path)") }
    return image
}

// ---- frames to H.264 ----
let names = try FileManager.default.contentsOfDirectory(atPath: frames.path).filter { $0.hasSuffix(".jpg") }.sorted()
guard !names.isEmpty else { fail("no frames in \(frames.path)") }
let first = image(frames.appendingPathComponent(names[0]))
let (width, height) = (first.width, first.height)
try? FileManager.default.removeItem(at: silent)
let writer = try AVAssetWriter(outputURL: silent, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
    AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: width, AVVideoHeightKey: height,
    AVVideoColorPropertiesKey: [AVVideoColorPrimariesKey: AVVideoColorPrimaries_ITU_R_709_2,
                                AVVideoTransferFunctionKey: AVVideoTransferFunction_ITU_R_709_2,
                                AVVideoYCbCrMatrixKey: AVVideoYCbCrMatrix_ITU_R_709_2],
    AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: 12_000_000,
                                      AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                                      AVVideoMaxKeyFrameIntervalKey: Int(timeline.fps) * 2]])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
    kCVPixelBufferWidthKey as String: width, kCVPixelBufferHeightKey as String: height])
writer.add(input)
guard writer.startWriting() else { fail("writer: \(String(describing: writer.error))") }
writer.startSession(atSourceTime: .zero)
let sRGB = CGColorSpace(name: CGColorSpace.sRGB)!
for (index, name) in names.enumerated() {
    autoreleasepool {
        while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.002) }
        var buffer: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &buffer)
        guard let pixels = buffer else { fail("no pixel buffer") }
        CVPixelBufferLockBaseAddress(pixels, [])
        let context = CGContext(data: CVPixelBufferGetBaseAddress(pixels), width: width, height: height, bitsPerComponent: 8,
                                bytesPerRow: CVPixelBufferGetBytesPerRow(pixels), space: sRGB,
                                bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)!
        context.draw(image(frames.appendingPathComponent(name)), in: CGRect(x: 0, y: 0, width: width, height: height))
        CVPixelBufferUnlockBaseAddress(pixels, [])
        if !adaptor.append(pixels, withPresentationTime: CMTime(value: CMTimeValue(index), timescale: timeline.fps)) {
            fail("append failed at frame \(index): \(String(describing: writer.error))")
        }
    }
}
input.markAsFinished()
let written = DispatchSemaphore(value: 0)
writer.finishWriting { written.signal() }
written.wait()
guard writer.status == .completed else { fail("writer: \(String(describing: writer.error))") }
print("wrote \(silent.lastPathComponent): \(names.count) frames, \(width)x\(height)")

// ---- add the narration, each line at its start time ----
let composition = AVMutableComposition()
let video = AVURLAsset(url: silent)
guard let videoTrack = video.tracks(withMediaType: .video).first,
      let compVideo = composition.addMutableTrack(withMediaType: .video, preferredTrackID: kCMPersistentTrackID_Invalid),
      let compAudio = composition.addMutableTrack(withMediaType: .audio, preferredTrackID: kCMPersistentTrackID_Invalid)
else { fail("cannot set up the composition") }
try compVideo.insertTimeRange(CMTimeRange(start: .zero, duration: video.duration), of: videoTrack, at: .zero)
var end = CMTime.zero
for clip in timeline.audio {
    let asset = AVURLAsset(url: URL(fileURLWithPath: clip.file))
    guard let track = asset.tracks(withMediaType: .audio).first else { fail("no audio in \(clip.file)") }
    let start = CMTime(seconds: clip.start, preferredTimescale: 48_000)
    if start > end { compAudio.insertEmptyTimeRange(CMTimeRange(start: end, end: start)) }
    try compAudio.insertTimeRange(CMTimeRange(start: .zero, duration: asset.duration), of: track, at: max(start, end))
    end = compAudio.timeRange.end
}
try? FileManager.default.removeItem(at: voiced)
guard let export = AVAssetExportSession(asset: composition, presetName: AVAssetExportPresetHighestQuality) else { fail("no export session") }
export.outputURL = voiced
export.outputFileType = .mp4
export.timeRange = CMTimeRange(start: .zero, duration: video.duration)
let exported = DispatchSemaphore(value: 0)
export.exportAsynchronously { exported.signal() }
exported.wait()
guard export.status == .completed else { fail("export: \(String(describing: export.error))") }
print("wrote \(voiced.lastPathComponent): \(String(format: "%.1f", video.duration.seconds)) s with \(timeline.audio.count) narration lines")
