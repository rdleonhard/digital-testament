# Testator Zero — iOS

The consumer face of the Testament Network: build the corpus of your
life, in life. The avatar interviews you (voice or keyboard), looks
through your camera and keeps only its impressions, talks with you, and
grows a standard [Digital Corpus](../../schema/corpus.schema.json) on
the phone — exportable any time, deployable later to a node, an ElizaOS
character, or a Testament Key. Subscription ("Remembrance") funds the
private inference; the corpus itself is the user's property, free to
take, forever. No Urbit in this app.

## Features

- **Talk** — chat with the avatar (Venice API); replies are spoken.
- **Ask me** — the curiosity engine: one question at a time, answers
  become memories. Speak answers via on-device speech recognition.
- **Look** — the eye: camera frame → vision model → first-person
  observation memory. The image is discarded; words only.
  (Simulator has no camera; a photo picker stands in.)
- **Corpus** — every memory, with one-tap export of the JSON.
- **Their own voice** — if the user records an iOS **Personal Voice**
  (Settings → Accessibility → Personal Voice), the avatar speaks with
  it: Apple's on-device voice clone, recorded by the living subject.
  Server-side cloning (voicebox-class) is roadmap.
- **Remembrance subscription** — StoreKit 2 auto-renewables
  ($9.99/mo, $99/yr), full flow testable in the simulator via the
  bundled `.storekit` config. (Digital subs must use in-app purchase
  per App Store rules; the native sheet charges Apple Pay cards.)

## Build

Requires full Xcode (not just Command Line Tools).

```sh
brew install xcodegen
cp Secrets.example.plist Secrets.plist   # add your Venice key
xcodegen generate
open TestatorZero.xcodeproj              # or build via Claude's simulator tools
```

Run the `TestatorZero` scheme (it carries the StoreKit configuration so
the paywall works with test transactions).

## Architecture notes

- `Corpus.swift` mirrors the network's corpus schema and ports the
  node's prompt builder (seed-first memory budgeting, mood tags).
- The will's constitution travels with the persona: disclosure,
  no-fabrication, and prohibited-uses are baked into the system prompt
  exactly as on every other Testament runtime.
- Dev builds read the Venice key from `Secrets.plist` (gitignored);
  production routes inference through a backend so no key ships in the
  binary.
