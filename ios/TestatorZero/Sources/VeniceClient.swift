import Foundation
import UIKit

// Venice API client (OpenAI-compatible). The subscription funds the Diem
// this spends; the key ships server-side in production — for development
// it reads Secrets.plist (gitignored).

enum VeniceError: LocalizedError {
    case noKey, badResponse(Int, String)
    var errorDescription: String? {
        switch self {
        case .noKey:
            return "No Venice API key. Add Secrets.plist (see Secrets.example.plist)."
        case let .badResponse(code, body):
            return "Venice \(code): \(body.prefix(140))"
        }
    }
}

struct VeniceClient {
    static let chatModel = "llama-3.3-70b"
    static let visionModel = "qwen3-vl-235b-a22b"
    private static let endpoint = URL(string: "https://api.venice.ai/api/v1/chat/completions")!

    static var apiKey: String? {
        guard let url = Bundle.main.url(forResource: "Secrets", withExtension: "plist"),
              let dict = NSDictionary(contentsOf: url),
              let key = dict["VENICE_API_KEY"] as? String, !key.isEmpty
        else { return nil }
        return key
    }

    static func chat(messages: [[String: Any]], model: String = chatModel,
                     maxTokens: Int = 400) async throws -> String {
        guard let key = apiKey else { throw VeniceError.noKey }
        var req = URLRequest(url: endpoint)
        req.httpMethod = "POST"
        req.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.timeoutInterval = 120
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "model": model, "messages": messages, "max_tokens": maxTokens,
        ])
        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 else {
            throw VeniceError.badResponse(code, String(data: data, encoding: .utf8) ?? "")
        }
        let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let choices = obj?["choices"] as? [[String: Any]]
        let msg = choices?.first?["message"] as? [String: Any]
        return (msg?["content"] as? String) ?? ""
    }

    static func describe(image: UIImage, systemPrompt: String) async throws -> String {
        let jpeg = image.jpegData(compressionQuality: 0.7) ?? Data()
        let dataURL = "data:image/jpeg;base64," + jpeg.base64EncodedString()
        let ask = "You just looked through your subject's camera. Describe in first person, in your own voice, what you see and what it suggests about the life you are learning. 2-4 sentences, warm and specific. This is a private diary entry — skip your disclosure line. Then the [mood: X] line."
        return try await chat(messages: [
            ["role": "system", "content": systemPrompt],
            ["role": "user", "content": [
                ["type": "text", "text": ask],
                ["type": "image_url", "image_url": ["url": dataURL]],
            ]],
        ], model: visionModel)
    }
}
