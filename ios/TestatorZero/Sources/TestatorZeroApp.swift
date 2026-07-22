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
    @StateObject private var settings = AppSettings()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(store)
                .environmentObject(subs)
                .environmentObject(voice)
                .environmentObject(settings)
                .preferredColorScheme(.dark)
                .tint(Theme.gold)
                .onChange(of: scenePhase) { _, phase in
                    if phase == .active { Task { await maybeTwilight() } }
                }
        }
    }

    // Opportunistic twilight: on app open, if the epoch is nearly over
    // and there's Diem to spend on the user's own key, reflect quietly.
    // (iOS can't guarantee a timed background wake, so we seize the open.)
    private func maybeTwilight() async {
        // Formulate & schedule the avatar's "texts" for the days ahead.
        await NudgeEngine.maybeRefill(store: store, settings: settings,
                                      subscribed: subs.subscribed)
        guard settings.autoTwilight, settings.usingOwnKey, store.corpus != nil else { return }
        if let last = settings.lastTwilight, Date().timeIntervalSince(last) < 3600 { return }
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed) else { return }
        guard let (diem, epoch) = try? await VeniceClient.diemBalance(key: key),
              TwilightEngine.shouldAutoRun(diem: diem, epoch: epoch) else { return }
        settings.lastTwilight = Date()
        _ = await TwilightEngine.run(store: store, key: key)
    }
}

struct RootView: View {
    @EnvironmentObject var store: CorpusStore

    var body: some View {
        Group {
            if store.corpus == nil {
                OnboardingView()
            } else {
                MainTabView() // free to enter; inference gated per-call
            }
        }
        .background(Theme.bg)
    }
}

struct MainTabView: View {
    @EnvironmentObject var store: CorpusStore
    @State private var tab = 0

    var body: some View {
        TabView(selection: $tab) {
            ChatView()
                .tabItem { Label("Talk", systemImage: "bubble.left.and.bubble.right") }
                .tag(0)
            InterviewView()
                .tabItem { Label("Ask me", systemImage: "questionmark.circle") }
                .tag(1)
            AddView()
                .tabItem { Label("Write", systemImage: "square.and.pencil") }
                .tag(2)
            MemoriesView()
                .tabItem { Label("Corpus", systemImage: "books.vertical") }
                .tag(3)
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(4)
        }
        .background(Theme.bg)
        .onAppear {
            // A newly woken avatar goes straight to its first question.
            if store.justWoke { tab = 1 }
        }
    }
}
