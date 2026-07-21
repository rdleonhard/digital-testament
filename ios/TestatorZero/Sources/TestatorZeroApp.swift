import SwiftUI

// Testator Zero — build the corpus of a life, in life.
// The consumer face of the Testament Network: interviews, observations,
// and conversation grow a Digital Corpus on this phone; the same JSON a
// will's Digital Executor can one day deploy to a node, an ElizaOS
// character, or a Testament Key.

enum Theme {
    static let bg = Color(red: 0.051, green: 0.067, blue: 0.090)      // #0d1117
    static let panel = Color(red: 0.086, green: 0.106, blue: 0.133)   // #161b22
    static let gold = Color(red: 0.831, green: 0.663, blue: 0.306)    // #d4a94e
    static let ink = Color(red: 0.902, green: 0.929, blue: 0.953)
    static let dim = Color(red: 0.545, green: 0.580, blue: 0.620)

    static func moodColor(_ mood: String) -> Color {
        switch mood {
        case "cheerful": return Color(red: 0.31, green: 0.79, blue: 0.48)
        case "pensive": return Color(red: 0.48, green: 0.64, blue: 0.97)
        case "wistful": return Color(red: 0.71, green: 0.56, blue: 0.68)
        case "alert": return Color(red: 0.88, green: 0.39, blue: 0.36)
        default: return gold // curious
        }
    }
}

@main
struct TestatorZeroApp: App {
    @StateObject private var store = CorpusStore()
    @StateObject private var subs = SubscriptionManager()
    @StateObject private var voice = VoiceManager()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .environmentObject(subs)
                .environmentObject(voice)
                .preferredColorScheme(.dark)
                .tint(Theme.gold)
        }
    }
}

struct RootView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var subs: SubscriptionManager

    var body: some View {
        Group {
            if store.corpus == nil {
                OnboardingView()
            } else if !subs.subscribed {
                PaywallView()
            } else {
                MainTabView()
            }
        }
        .background(Theme.bg)
    }
}

struct MainTabView: View {
    var body: some View {
        TabView {
            ChatView()
                .tabItem { Label("Talk", systemImage: "bubble.left.and.bubble.right") }
            InterviewView()
                .tabItem { Label("Ask me", systemImage: "questionmark.circle") }
            ObserveView()
                .tabItem { Label("Look", systemImage: "eye") }
            MemoriesView()
                .tabItem { Label("Corpus", systemImage: "books.vertical") }
        }
        .background(Theme.bg)
    }
}
