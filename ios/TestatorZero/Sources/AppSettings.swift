import SwiftUI

// User settings. The app is free: bring your own Venice key and it costs
// you nothing. Our default inference (the bundled key) is the paid
// convenience, gated by the Remembrance subscription.

@MainActor
final class AppSettings: ObservableObject {
    @Published var customKey: String {
        didSet { UserDefaults.standard.set(customKey, forKey: Self.keyDefault) }
    }
    @Published var speakReplies: Bool {
        didSet { UserDefaults.standard.set(speakReplies, forKey: "speak_replies") }
    }
    @Published var autoTwilight: Bool {
        didSet { UserDefaults.standard.set(autoTwilight, forKey: "auto_twilight") }
    }
    var lastTwilight: Date? {
        get { UserDefaults.standard.object(forKey: "last_twilight") as? Date }
        set { UserDefaults.standard.set(newValue, forKey: "last_twilight") }
    }

    private static let keyDefault = "venice_custom_key"

    init() {
        customKey = UserDefaults.standard.string(forKey: Self.keyDefault) ?? ""
        speakReplies = UserDefaults.standard.object(forKey: "speak_replies") as? Bool ?? true
        autoTwilight = UserDefaults.standard.object(forKey: "auto_twilight") as? Bool ?? true
    }

    var usingOwnKey: Bool {
        !customKey.trimmingCharacters(in: .whitespaces).isEmpty
    }
}
