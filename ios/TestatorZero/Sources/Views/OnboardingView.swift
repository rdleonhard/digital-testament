import SwiftUI

struct OnboardingView: View {
    @EnvironmentObject var store: CorpusStore
    @EnvironmentObject var voice: VoiceManager
    @State private var name = ""
    @State private var firstMemory = ""

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                Text("TESTATOR ZERO")
                    .font(.system(.title2, design: .monospaced).weight(.semibold))
                    .kerning(4)
                    .foregroundStyle(Theme.gold)
                    .padding(.top, 48)

                Text("Build the corpus of your life, in life.")
                    .font(.title3.weight(.medium))
                    .foregroundStyle(Theme.ink)

                Text("Your avatar starts almost empty — a curiosity with your name. It interviews you, looks where you let it, and remembers. What grows here is a Digital Corpus: a portable JSON of who you are, yours to export, strong enough to outlast you.")
                    .foregroundStyle(Theme.dim)

                VStack(alignment: .leading, spacing: 8) {
                    Text("What should it call itself?")
                        .font(.subheadline).foregroundStyle(Theme.dim)
                    TextField("Your name", text: $name)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Theme.panel, in: RoundedRectangle(cornerRadius: 10))
                        .foregroundStyle(Theme.ink)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("A first memory to seed it (optional)")
                        .font(.subheadline).foregroundStyle(Theme.dim)
                    TextField("Where does your story start?", text: $firstMemory, axis: .vertical)
                        .lineLimit(3 ... 6)
                        .textFieldStyle(.plain)
                        .padding(12)
                        .background(Theme.panel, in: RoundedRectangle(cornerRadius: 10))
                        .foregroundStyle(Theme.ink)
                }

                Button {
                    store.begin(name: name.trimmingCharacters(in: .whitespaces),
                                firstMemory: firstMemory)
                    voice.requestPermissions()
                } label: {
                    Text("Wake the avatar")
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(name.trimmingCharacters(in: .whitespaces).isEmpty)

                Text("It will always say what it is. It never invents your life. It cannot sign, promise, or advise. Those aren't features — they're its constitution.")
                    .font(.footnote)
                    .foregroundStyle(Theme.dim)
            }
            .padding(24)
        }
        .background(Theme.bg)
    }
}
