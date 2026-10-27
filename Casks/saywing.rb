cask "saywing" do
  version "0.1.30,130"

  on_arm do
    sha256 "c95b8a6aafed04ca9f4bd67f6236691af0cbadd1668314a6ca0f61f2edf95fb4"

    url "https://www.christopherboebel.com/downloads/saywing/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end
  on_intel do
    sha256 "c37d6b2936d6184d87815d073fe47eca41defb6aa33350ed757c7e5d31864c91"

    url "https://www.christopherboebel.com/downloads/saywing/x86_64/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end

  name "Saywing"
  desc "Reads on-screen text aloud and transcribes speech, fully on-device"
  homepage "https://github.com/ChrBoebel/saywing"

  livecheck do
    url "https://www.christopherboebel.com/downloads/saywing/latest.json"
    strategy :json do |json|
      version = json["version"]
      build = json["build"]
      next if version.blank? || build.blank?

      "#{version},#{build}"
    end
  end

  auto_updates true
  depends_on macos: :sonoma

  app "Saywing.app"

  zap trash: [
    "~/Library/Application Support/Saywing",
    "~/Library/Caches/com.christopherbobel.OpenScreenReader",
    "~/Library/HTTPStorages/com.christopherbobel.OpenScreenReader",
    "~/Library/Preferences/com.christopherbobel.OpenScreenReader.plist",
  ]
end
