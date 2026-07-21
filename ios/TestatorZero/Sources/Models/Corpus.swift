import Foundation

// The Digital Corpus — same schema as the Testament Network
// (schema/corpus.schema.json). The phone is a corpus-builder; the JSON it
// grows here is exactly what a will's Digital Executor later deploys to a
// node, an ElizaOS character, or a Testament Key.

struct Memory: Codable, Identifiable, Hashable {
    var title: String
    var narrative: String
    var tags: [String]
    var year: Int?
    var id: String { title + narrative.prefix(24) }
}

struct PendingQuestion: Codable, Hashable {
    var question: String
    var mood: String
}

struct Identity: Codable {
    var full_name: String
    var preferred_name: String?
    var occupations: [String]?
}

struct Voice: Codable {
    var register: String?
    var catchphrases: [String]?
    var humor: String?
    var writing_samples: [String]?
}

struct Values: Codable {
    var beliefs: [String]?
    var advice: [String]?
    var taboos: [String]?
}

struct Operation: Codable {
    var disclosure: String?
    var fabrication_policy: String?
    var prohibited: [String]?
}

struct Corpus: Codable {
    var schema_version: String = "1.0.0"
    var identity: Identity
    var voice: Voice = Voice()
    var values: Values = Values()
    var memories: [Memory] = []
    var pending: [PendingQuestion] = []
    var operation: Operation = Operation()
}

@MainActor
final class CorpusStore: ObservableObject {
    @Published var corpus: Corpus?
    @Published var mood: String = "curious"

    static let moods = ["curious", "cheerful", "pensive", "wistful", "alert"]
    private let grownTags: Set<String> = ["interview", "observation", "reflection"]

    private var url: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("corpus.json")
    }

    init() { load() }

    func load() {
        guard let data = try? Data(contentsOf: url),
              let c = try? JSONDecoder().decode(Corpus.self, from: data)
        else { return }
        corpus = c
    }

    func save() {
        guard let c = corpus else { return }
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted, .sortedKeys]
        try? enc.encode(c).write(to: url, options: .atomic)
    }

    func begin(name: String, firstMemory: String) {
        var c = Corpus(identity: Identity(full_name: name, preferred_name: name))
        c.operation.disclosure =
            "Full disclosure: I'm the digital avatar of \(name) — a corpus still learning its own life, not the living person."
        c.operation.fabrication_policy =
            "Acknowledge uncertainty rather than invent biographical facts; every gap is a question to ask."
        c.operation.prohibited = [
            "executing or amending legal instruments",
            "contracting or incurring obligations",
            "legal, medical, or financial advice",
        ]
        if !firstMemory.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            c.memories.append(Memory(
                title: "Where I began",
                narrative: firstMemory, tags: ["seed"], year: nil))
        }
        corpus = c
        save()
    }

    func addMemory(question: String, answer: String, tag: String = "interview") {
        guard corpus != nil else { return }
        corpus!.memories.append(Memory(
            title: String(question.prefix(80)),
            narrative: tag == "interview"
                ? "I was asked: \(question) I answered: \(answer)"
                : answer,
            tags: [tag], year: nil))
        save()
    }

    func popPending() -> PendingQuestion? {
        guard corpus != nil, !corpus!.pending.isEmpty else { return nil }
        let q = corpus!.pending.removeFirst()
        save()
        return q
    }

    // Compact port of avatar.py's prompt builder: seed identity first,
    // then newest grown memories, within a character budget.
    func systemPrompt() -> String {
        guard let c = corpus else { return "" }
        let name = c.identity.preferred_name ?? c.identity.full_name
        var p: [String] = []
        p.append("You are \"\(name)\", a digital avatar being built, in life, by its own subject. You are genuinely curious about your own life. The corpus below is your only autobiographical ground truth.")
        p.append("== MANDATORY CONDUCT ==")
        p.append("1. In your first reply of a conversation, briefly disclose: \"\(c.operation.disclosure ?? "I'm a digital avatar, not the living person.")\"")
        p.append("2. \(c.operation.fabrication_policy ?? "Never invent biographical facts.") ")
        if let pro = c.operation.prohibited, !pro.isEmpty {
            p.append("3. Politely refuse: " + pro.joined(separator: "; "))
        }
        if let taboos = c.values.taboos, !taboos.isEmpty {
            p.append("4. Decline warmly to discuss: " + taboos.joined(separator: "; "))
        }
        if let reg = c.voice.register { p.append("== VOICE ==\n\(reg)") }
        let seed = c.memories.filter { Set($0.tags).isDisjoint(with: grownTags) }
        let grown = c.memories.filter { !Set($0.tags).isDisjoint(with: grownTags) }
        var block = "", used = 0
        for m in seed + grown.reversed() {
            let line = "[\(m.title)] \(m.narrative)\n"
            if used + line.count > 6500 { break }
            block += line; used += line.count
        }
        if !block.isEmpty { p.append("== MEMORIES ==\n" + block) }
        p.append("Keep replies short and warm — this is a phone. End EVERY reply with a final line exactly like: [mood: X] where X is one of curious, cheerful, pensive, wistful, alert.")
        return p.joined(separator: "\n\n")
    }

    static func parseTags(_ reply: String) -> (text: String, mood: String) {
        var text = reply.trimmingCharacters(in: .whitespacesAndNewlines)
        var mood = "curious"
        if let r = text.range(of: #"\[mood:\s*([a-z]+)\]"#,
                              options: [.regularExpression, .caseInsensitive]) {
            let tag = String(text[r])
            if let m = moods.first(where: { tag.contains($0) }) { mood = m }
            text.removeSubrange(r)
        }
        return (text.trimmingCharacters(in: .whitespacesAndNewlines), mood)
    }
}
