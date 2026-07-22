import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @State private var page = 0
    @State private var name = ""
    @State private var firstMemory = ""

    var body: some View {
        TabView(selection: $page) {
            hook.tag(0)
            how.tag(1)
            wake.tag(2)
        }
        .tabViewStyle(.page(indexDisplayMode: .automatic))
        .background(Theme.bg)
        .ignoresSafeArea(.keyboard, edges: .bottom)
    }

    private var hook: some View {
        VStack(spacing: 26) {
            Spacer()
            FlameView(mood: "curious", size: 84)
            Text("Someday, someone\nwill ask who you were.")
                .font(.system(.largeTitle, design: .serif).weight(.medium))
                .multilineTextAlignment(.center)
                .foregroundStyle(Theme.ink)
            Text("Testator Zero builds the answer while you're here to give it — a living archive of your memories, in your own words, that can outlast you.")
                .multilineTextAlignment(.center)
                .foregroundStyle(Theme.dim)
                .padding(.horizontal, 36)
            Spacer()
            Button { withAnimation { page = 1 } } label: {
                Text("Begin").frame(maxWidth: .infinity).padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .padding(.horizontal, 28)
            .padding(.bottom, 40)
        }
    }

    private var how: some View {
        VStack(alignment: .leading, spacing: 26) {
            Spacer()
            Text("A tiny ritual,\na vast result.")
                .font(.system(.largeTitle, design: .serif).weight(.medium))
                .foregroundStyle(Theme.ink)
            row(icon: "questionmark.bubble", title: "It interviews you",
                text: "One good question a day. Answer by voice; it becomes a memory.")
            row(icon: "eye", title: "It sees what you show it",
                text: "Point the camera at a moment. It keeps the impression — never the photo.")
            row(icon: "moon.stars", title: "It reflects at twilight",
                text: "Each evening it weaves your memories into who you're becoming.")
            row(icon: "square.and.arrow.up", title: "It's yours, forever",
                text: "The archive exports as one portable file. No lock-in, even in death.")
            Spacer()
            Button { withAnimation { page = 2 } } label: {
                Text("Wake it up").frame(maxWidth: .infinity).padding(.vertical, 14)
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom, 40)
        }
        .padding(.horizontal, 30)
    }

    private func row(icon: String, title: String, text: String) -> some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: icon)
                .font(.title3).foregroundStyle(Theme.gold).frame(width: 30)
            VStack(alignment: .leading, spacing: 3) {
                Text(title).font(.headline).foregroundStyle(Theme.ink)
                Text(text).font(.subheadline).foregroundStyle(Theme.dim)
            }
        }
    }

    private var wake: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack { Spacer(); FlameView(mood: "curious", size: 56); Spacer() }
                    .padding(.top, 60)
                Text("Give it your name.")
                    .font(.system(.title, design: .serif).weight(.medium))
                    .foregroundStyle(Theme.ink)
                TextField("Your name", text: $name)
                    .textFieldStyle(.plain)
                    .padding(14)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 12))
                    .foregroundStyle(Theme.ink)
                Text("And, if you like, a first memory to seed it:")
                    .font(.subheadline).foregroundStyle(Theme.dim)
                TextField("Where does your story start?", text: $firstMemory, axis: .vertical)
                    .lineLimit(3 ... 6)
                    .textFieldStyle(.plain)
                    .padding(14)
                    .background(Theme.panel, in: RoundedRectangle(cornerRadius: 12))
                    .foregroundStyle(Theme.ink)
                Button {
                    store.begin(name: name.trimmingCharacters(in: .whitespaces),
                                firstMemory: firstMemory)
                    store.justWoke = true
                    voice.requestPermissions()
                    Haptics.success()
                } label: {
                    Label("Light the flame", systemImage: "flame")
                        .frame(maxWidth: .infinity).padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)
                Text("It never invents your life, and it can't sign, promise, or advise. That's not a limitation — it's its constitution.")
                    .font(.footnote).foregroundStyle(Theme.dim)
            }
            .padding(28)
        }
        .scrollDismissesKeyboard(.interactively)
    }
}
