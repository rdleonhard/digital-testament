import Foundation
import UIKit

// Venice API client (OpenAI-compatible). The subscription funds the Diem
// this spends; the key ships server-side in production — for development
// it reads Secrets.plist (gitignored).

enum VeniceError: LocalizedError {
    case needsEntitlement, badResponse(Int, String)
    var errorDescription: String? {
        switch self {
        case .needsEntitlement:
            return "Add your own Venice key in Settings (free), or subscribe to use our inference."
        case let .badResponse(code, body):
            return "Venice \(code): \(body.prefix(140))"
        }
    }
}

struct VeniceClient {
    static let chatModel = "llama-3.3-70b"
    static let visionModel = "qwen3-vl-235b-a22b"
    private static let endpoint = URL(string: "https://api.venice.ai/api/v1/chat/completions")!

    // Our default (bundled) key — the paid convenience, subscription-gated.
    static var bundledKey: String? {
        let docs = FileManager.default.urls(for: .documentDirectory,
                                            in: .userDomainMask).first?
            .appendingPathComponent("Secrets.plist")
        for url in [docs, Bundle.main.url(forResource: "Secrets", withExtension: "plist")].compactMap({ $0 }) {
            if let dict = NSDictionary(contentsOf: url),
               let key = dict["VENICE_API_KEY"] as? String, !key.isEmpty {
                return key
            }
        }
        return nil
    }

    // The app is free with your own key; our key needs a subscription.
    static func activeKey(customKey: String, subscribed: Bool) -> String? {
        let own = customKey.trimmingCharacters(in: .whitespaces)
        if !own.isEmpty { return own }
        return subscribed ? bundledKey : nil
    }

    static func chat(messages: [[String: Any]], key: String,
                     model: String = chatModel,
                     maxTokens: Int = 400) async throws -> String {
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

    // Remaining daily Diem and when the epoch turns (for twilight).
    static func diemBalance(key: String) async throws -> (diem: Double, epoch: String) {
        var req = URLRequest(url: URL(string: "https://api.venice.ai/api/v1/api_keys/rate_limits")!)
        req.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
        req.timeoutInterval = 30
        let (data, resp) = try await URLSession.shared.data(for: req)
        let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
        guard code == 200 else {
            throw VeniceError.badResponse(code, String(data: data, encoding: .utf8) ?? "")
        }
        let obj = try JSONSerialization.jsonObject(with: data) as? [String: Any]
        let d = obj?["data"] as? [String: Any]
        let balances = d?["balances"] as? [String: Any]
        let diem = (balances?["DIEM"] as? Double) ?? 0
        let epoch = (d?["nextEpochBegins"] as? String) ?? ""
        return (diem, epoch)
    }

    static func describe(image: UIImage, systemPrompt: String,
                         key: String) async throws -> String {
        let jpeg = image.jpegData(compressionQuality: 0.7) ?? Data()
        let dataURL = "data:image/jpeg;base64," + jpeg.base64EncodedString()
        let ask = "You just looked through your subject's camera. Describe in first person, in your own voice, what you see and what it suggests about the life you are learning. 2-4 sentences, warm and specific. This is a private diary entry. Then the [mood: X] line."
        return try await chat(messages: [
            ["role": "system", "content": systemPrompt],
            ["role": "user", "content": [
                ["type": "text", "text": ask],
                ["type": "image_url", "image_url": ["url": dataURL]],
            ]],
        ], key: key, model: visionModel)
    }
}
