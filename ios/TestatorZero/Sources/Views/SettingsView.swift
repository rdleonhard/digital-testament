import StoreKit
import SwiftUI

struct SettingsView: View {
    @EnvironmentObject var settings: AppSettings
    @EnvironmentObject var subs: SubscriptionManager
    @EnvironmentObject var voice: VoiceManager
    @EnvironmentObject var store: CorpusStore
    @State private var showPaywall = false
    @State private var twilightRunning = false
    @State private var twilightLog = ""

    private var status: String {
        if settings.usingOwnKey { return "Using your own Venice key — free, unlimited." }
        if subs.subscribed { return "Remembrance active — using our inference." }
        return "No inference yet. Add your key below (free) or subscribe."
    }

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text(status).foregroundStyle(settings.usingOwnKey || subs.subscribed ? Theme.gold : Theme.dim)
                        .font(.subheadline)
                } header: { Text("Inference") }

                Section {
                    SecureField("vk-... paste your Venice API key", text: $settings.customKey)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .foregroundStyle(Theme.ink)
                    if settings.usingOwnKey {
                        Button("Clear key", role: .destructive) { settings.customKey = "" }
                    }
                } header: {
                    Text("Bring your own key (free)")
                } footer: {
                    Text("With your own Venice key the app is free — your avatar thinks on your dime, and nothing is billed by us. Get one at venice.ai.")
                }

                Section {
                    if subs.subscribed {
                        Label("Remembrance active", systemImage: "checkmark.seal")
                            .foregroundStyle(Theme.gold)
                        Button("Manage subscription") {
                            Task { await subs.restore() }
                        }
                    } else {
                        Button("See Remembrance plans") { showPaywall = true }
                            .foregroundStyle(Theme.gold)
                    }
                    Button("Restore purchases") { Task { await subs.restore() } }
                        .font(.footnote).foregroundStyle(Theme.dim)
                } header: {
                    Text("Or use our inference (subscription)")
                } footer: {
                    Text("Prefer not to manage a key? Remembrance runs your avatar on our private inference. Either way, your corpus is yours and exports free.")
                }

                Section {
                    if settings.usingOwnKey {
                        Toggle("Reflect near each epoch's end", isOn: $settings.autoTwilight)
                            .tint(Theme.gold)
                        Button {
                            Task { await runTwilight() }
                        } label: {
                            HStack {
                                Label(twilightRunning ? "reflecting…" : "Reflect now",
                                      systemImage: "moon.stars")
                                if twilightRunning { Spacer(); ProgressView().tint(Theme.gold) }
                            }
                        }
                        .disabled(twilightRunning)
                        .foregroundStyle(Theme.gold)
                        if !twilightLog.isEmpty {
                            Text(twilightLog).font(.caption).foregroundStyle(Theme.dim)
                        }
                    } else {
                        Text("Twilight reflections run on your own Venice key — add one above to let your avatar spend its expiring daily allocation on thinking about itself.")
                            .font(.footnote).foregroundStyle(Theme.dim)
                    }
                } header: {
                    Text("Twilight")
                } footer: {
                    Text("Diem doesn't roll over. As the daily epoch closes, your avatar spends what's left on reflections, memory-weaves, and questions it banks for you — an impression that accretes, epoch after epoch.")
                }

                Section {
                    Toggle("Speak replies aloud", isOn: $settings.speakReplies)
                        .tint(Theme.gold)
                    HStack {
                        Text("Personal Voice")
                        Spacer()
                        Text(voice.personalVoiceReady ? "ready" : "not set up")
                            .foregroundStyle(Theme.dim)
                    }
                } header: {
                    Text("Voice")
                } footer: {
                    Text("Record a Personal Voice in Settings → Accessibility → Personal Voice, and your avatar will speak in your own voice — cloned on-device by Apple.")
                }
            }
            .scrollContentBackground(.hidden)
            .background(Theme.bg)
            .navigationTitle("Settings")
            .sheet(isPresented: $showPaywall) { PaywallView() }
            .onAppear { voice.requestPermissions() }
        }
    }

    private func runTwilight() async {
        guard let key = VeniceClient.activeKey(customKey: settings.customKey,
                                               subscribed: subs.subscribed),
              settings.usingOwnKey else { return }
        twilightRunning = true
        twilightLog = "reading the epoch…"
        let s = await TwilightEngine.run(store: store, key: key) { line in
            twilightLog = line
        }
        settings.lastTwilight = Date()
        twilightRunning = false
        twilightLog = "Spent \(String(format: "%.2f", s.startedDiem - s.endedDiem)) Diem: \(s.reflections) reflections, \(s.wondered) questions banked."
    }
}
