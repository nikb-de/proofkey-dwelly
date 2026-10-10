import Foundation
import Vision
import ImageIO

struct Observation: Codable {
    let text: String
    let confidence: Float
    let box: [String: Double]
}
struct Result: Codable {
    let extractor: String
    let qualification: String
    let text: String
    let coordinateSystem: String
    let requestRevision: Int
    let observations: [Observation]
}

guard CommandLine.arguments.count == 2 else { exit(2) }
let url = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
if #available(macOS 13.0, *) { request.automaticallyDetectsLanguage = true }
do {
    try VNImageRequestHandler(url: url).perform([request])
    var observations: [Observation] = []
    for item in request.results ?? [] {
        guard let candidate = item.topCandidates(1).first else { continue }
        let box = item.boundingBox
        let coordinates: [String: Double] = ["x": Double(box.origin.x), "y": Double(box.origin.y),
                                            "width": Double(box.size.width), "height": Double(box.size.height)]
        observations.append(Observation(text: candidate.string, confidence: candidate.confidence,
                                        box: coordinates))
    }
    observations.sort { left, right in
        let leftY = left.box["y"] ?? 0.0
        let rightY = right.box["y"] ?? 0.0
        if abs(leftY - rightY) > 0.01 { return leftY > rightY }
        return (left.box["x"] ?? 0.0) < (right.box["x"] ?? 0.0)
    }
    let result = Result(extractor: "Apple Vision VNRecognizeTextRequest accurate; language correction disabled",
                        qualification: "unverified_ocr_visible_text_only",
                        text: observations.map(\.text).joined(separator: "\n") + "\n",
                        coordinateSystem: "normalized_bottom_left_origin",
                        requestRevision: request.revision, observations: observations)
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    FileHandle.standardOutput.write(try encoder.encode(result))
} catch {
    FileHandle.standardError.write(Data("ocr_failed\n".utf8))
    exit(1)
}
