cask "saywing" do
  version "0.1.31,131"

  on_arm do
    sha256 "3fe8d125045022aef3c470195d17c1ed7410e39e61c637b6149397267fbe5f96"

    url "https://www.christopherboebel.com/downloads/saywing/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end
  on_intel do
    sha256 "bad1a6b64542eaf1c1ecf61c49725a20ede878269e9774135f213c02f13620d6"

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
