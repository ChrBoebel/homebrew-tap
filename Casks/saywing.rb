cask "saywing" do
  version "0.1.32,132"

  on_arm do
    sha256 "ae40929720d5d973429e0360ff7a9ff476b898df492ba22970bb42a1acb81ac4"

    url "https://www.christopherboebel.com/downloads/saywing/Saywing-#{version.csv.first}-#{version.csv.second}.dmg"
  end
  on_intel do
    sha256 "ac009851d963151f76f33cc01623a17b8ecdf605f830ebd11ad3b733c001bf32"

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
